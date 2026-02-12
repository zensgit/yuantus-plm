"""
Job Worker
A simple worker process to poll and execute ConversionJobs.
"""

import time
import logging
import threading
import inspect
import contextvars
from typing import Callable, Dict, Any, Optional
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.database import get_db_session
from yuantus.meta_engine.models.job import ConversionJob  # For type hinting
from yuantus.meta_engine.services.cad_service import CadService  # Import CadService
from yuantus.context import org_id_var, tenant_id_var, user_id_var

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, worker_id: str, poll_interval: int = 5):
        self.worker_id = worker_id
        self.poll_interval = poll_interval  # seconds
        self.task_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None  # To hold the worker thread

    def register_handler(
        self, task_type: str, handler: Callable[[Dict[str, Any]], Any]
    ):
        """Registers a handler function for a specific task type."""
        self.task_handlers[task_type] = handler
        logger.info(
            f"Worker '{self.worker_id}' registered handler for task type: {task_type}"
        )

    def run_once(self) -> bool:
        """Polls and processes one job in the current thread. Returns True if a job was processed."""
        try:
            with get_db_session() as session:
                job_service = JobService(session)
                requeued = job_service.requeue_stale_jobs()
                if requeued:
                    logger.warning(
                        "Worker '%s' requeued %s stale job(s)", self.worker_id, requeued
                    )
                job: Optional[ConversionJob] = job_service.poll_next_job(self.worker_id)
                if job:
                    logger.info(
                        f"Worker '{self.worker_id}' picked up job {job.id} ({job.task_type})"
                    )
                    self._execute_job(job, job_service)
                    return True
        except Exception as e:
            logger.error(
                f"Worker '{self.worker_id}' error in run_once: {e}", exc_info=True
            )
        return False

    def start(self):
        """Starts the worker, polling for jobs in a separate thread."""
        if self._running:
            logger.warning(f"Worker '{self.worker_id}' is already running.")
            return

        logger.info(f"Worker '{self.worker_id}' starting...")
        self._running = True
        ctx = contextvars.copy_context()
        self._thread = threading.Thread(
            target=ctx.run, args=(self._run_loop,), name=f"Worker-{self.worker_id}-Loop"
        )
        # self._thread.daemon = True # Allow main program to exit even if worker is running
        self._thread.start()

    def _run_loop(self):
        """The main polling loop for the worker thread."""
        while self._running:
            try:
                with get_db_session() as session:
                    job_service = JobService(session)
                    requeued = job_service.requeue_stale_jobs()
                    if requeued:
                        logger.warning(
                            "Worker '%s' requeued %s stale job(s)",
                            self.worker_id,
                            requeued,
                        )
                    job: Optional[ConversionJob] = job_service.poll_next_job(
                        self.worker_id
                    )
                    if job:
                        logger.info(
                            f"Worker '{self.worker_id}' picked up job {job.id} ({job.task_type})"
                        )
                        self._execute_job(job, job_service)
                    else:
                        logger.debug(
                            f"Worker '{self.worker_id}' found no pending jobs. Sleeping..."
                        )
            except Exception as e:
                logger.error(
                    f"Worker '{self.worker_id}' encountered an error during polling: {e}",
                    exc_info=True,
                )
            finally:
                time.sleep(self.poll_interval)

    def stop(self):
        """Stops the worker and waits for its thread to finish."""
        if not self._running:
            logger.warning(f"Worker '{self.worker_id}' is not running.")
            return

        logger.info(
            f"Worker '{self.worker_id}' stopping. Waiting for thread to join..."
        )
        self._running = False
        if self._thread:
            self._thread.join(
                timeout=self.poll_interval + 1
            )  # Give it a chance to finish current poll/task
            if self._thread.is_alive():
                logger.warning(
                    f"Worker '{self.worker_id}' thread did not terminate gracefully."
                )
        logger.info(f"Worker '{self.worker_id}' stopped.")

    def _execute_job(self, job: ConversionJob, job_service: JobService):
        """Executes a single job."""
        tenant_token = None
        org_token = None
        user_token = None
        # Reload in case the API updated the payload after claim/dedupe (e.g. promote cad_dedup_vision to index=true).
        try:
            job_service.session.refresh(job)
        except Exception:
            pass
        payload = job.payload or {}

        tenant_id = payload.get("tenant_id")
        org_id = payload.get("org_id")
        user_id = payload.get("user_id") or job.created_by_id

        if tenant_id:
            tenant_token = tenant_id_var.set(str(tenant_id))
        if org_id:
            org_token = org_id_var.set(str(org_id))
        if user_id:
            user_token = user_id_var.set(str(user_id))

        def _job_context() -> dict:
            return {
                "job_id": job.id,
                "task_type": job.task_type,
                "file_id": payload.get("file_id"),
                "item_id": payload.get("item_id"),
                "tenant_id": payload.get("tenant_id"),
                "org_id": payload.get("org_id"),
                "user_id": payload.get("user_id") or job.created_by_id,
                "cad_connector_id": payload.get("cad_connector_id"),
                "source_path": payload.get("source_path"),
            }

        def _format_ctx(ctx: dict) -> str:
            parts = []
            for key in (
                "job_id",
                "task_type",
                "file_id",
                "item_id",
                "tenant_id",
                "org_id",
                "user_id",
                "cad_connector_id",
                "source_path",
            ):
                value = ctx.get(key)
                if value:
                    parts.append(f"{key}={value}")
            return " ".join(parts)

        def _classify_error(exc: Exception, message: str) -> str:
            text = (message or str(exc) or "").lower()
            if "source file missing" in text:
                return "source_missing"
            if "missing file_id" in text:
                return "missing_file_id"
            if "file not found" in text:
                return "file_not_found"
            if "connector" in text:
                return "connector_failed"
            if isinstance(exc, JobFatalError):
                return "fatal"
            if "no handler registered" in text:
                return "handler_missing"
            return "job_failed"

        try:
            ctx = _job_context()
            logger.info(
                "Worker '%s' executing job %s",
                self.worker_id,
                _format_ctx(ctx),
            )
            if job.task_type not in self.task_handlers:
                error_msg = f"No handler registered for task type: {job.task_type}"
                logger.error("%s %s", error_msg, _format_ctx(ctx))
                job_service.fail_job(
                    job.id,
                    error_msg,
                    error_code="handler_missing",
                    retry=False,
                )
                return

            try:
                handler = self.task_handlers[job.task_type]
                # Handlers should return a result or raise an exception.
                # If the handler supports (payload, session), pass the current DB session to avoid nested sessions.
                try:
                    params = list(inspect.signature(handler).parameters.values())
                    if len(params) >= 3:
                        result = handler(job.payload, job_service.session, job.id)
                    elif len(params) >= 2:
                        result = handler(job.payload, job_service.session)
                    else:
                        result = handler(job.payload)
                except (TypeError, ValueError):
                    result = handler(job.payload)

                # Post-processing: Sync attributes if present (Phase II CAD Integration)
                if isinstance(result, dict) and result.get("extracted_attributes"):
                    item_id = job.payload.get("item_id")
                    if item_id:
                        try:
                            # Use session from job_service
                            cad_service = CadService(job_service.session)
                            cad_service.sync_attributes_to_item(
                                item_id=item_id,
                                extracted_attributes=result["extracted_attributes"],
                                user_id=job.created_by_id or 1,
                            )
                            logger.info(
                                f"Worker '{self.worker_id}' synced attributes for Item {item_id}"
                            )
                        except Exception as sync_err:
                            logger.error(
                                f"Failed to sync attributes for job {job.id}: {sync_err}"
                            )
                            # We log but don't fail the job if sync fails, as conversion succeeded

                ctx = _job_context()
                logger.info(
                    "Worker '%s' completed job %s result_keys=%s",
                    self.worker_id,
                    _format_ctx(ctx),
                    sorted(result.keys()) if isinstance(result, dict) else None,
                )
                job_service.complete_job(job.id, result=result)
            except JobFatalError as e:
                error_msg = f"Job {job.id} fatal error: {e}"
                ctx = _job_context()
                error_code = _classify_error(e, error_msg)
                logger.error("%s %s", error_msg, _format_ctx(ctx))
                job_service.fail_job(
                    job.id,
                    error_msg,
                    retry=False,
                    error_code=error_code,
                )
            except Exception as e:
                error_msg = f"Job {job.id} execution failed: {e}"
                ctx = _job_context()
                error_code = _classify_error(e, error_msg)
                logger.error("%s %s", error_msg, _format_ctx(ctx), exc_info=True)
                job_service.fail_job(
                    job.id,
                    error_msg,
                    error_code=error_code,
                )
        finally:
            if user_token is not None:
                user_id_var.reset(user_token)
            if org_token is not None:
                org_id_var.reset(org_token)
            if tenant_token is not None:
                tenant_id_var.reset(tenant_token)
