from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_method_block(text: str, *, method_name: str) -> str:
    lines = text.splitlines()
    start = None
    indent = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith(f"def {method_name}("):
            start = i
            indent = len(line) - len(line.lstrip())
            break
    assert start is not None and indent is not None, f"Missing method: {method_name}"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        this_indent = len(line) - len(line.lstrip())
        if this_indent == indent and line.lstrip().startswith("def "):
            end = j
            break
    return "\n".join(lines[start:end])


def _index(block: str, needle: str) -> int:
    idx = block.find(needle)
    assert idx != -1, f"Missing expected snippet: {needle!r}"
    return idx


def test_poll_next_job_uses_skip_locked_on_postgres() -> None:
    repo_root = _find_repo_root(Path(__file__))
    svc = repo_root / "src" / "yuantus" / "meta_engine" / "services" / "job_service.py"
    assert svc.is_file()
    block = _extract_method_block(_read(svc), method_name="poll_next_job")

    assert 'dialect == "postgresql"' in block
    assert "with_for_update(skip_locked=True)" in block

    # Ensure we apply SKIP LOCKED before selecting a row.
    assert _index(block, "with_for_update(skip_locked=True)") < _index(block, "query.first()")


def test_poll_next_job_claims_processing_fields_before_commit() -> None:
    repo_root = _find_repo_root(Path(__file__))
    svc = repo_root / "src" / "yuantus" / "meta_engine" / "services" / "job_service.py"
    assert svc.is_file()
    block = _extract_method_block(_read(svc), method_name="poll_next_job")

    commit_idx = _index(block, "self.session.commit()")

    # Critical fields must be updated as part of the claim transaction.
    assert _index(block, "job.status = JobStatus.PROCESSING.value") < commit_idx
    assert _index(block, "job.worker_id = worker_id") < commit_idx
    assert _index(block, "job.started_at = datetime.utcnow()") < commit_idx
    assert _index(block, "job.attempt_count += 1") < commit_idx


def test_poll_next_job_queue_filters_are_stable() -> None:
    repo_root = _find_repo_root(Path(__file__))
    svc = repo_root / "src" / "yuantus" / "meta_engine" / "services" / "job_service.py"
    assert svc.is_file()
    block = _extract_method_block(_read(svc), method_name="poll_next_job")

    # Guard against accidental changes that break the queue index usefulness.
    assert "ConversionJob.status == JobStatus.PENDING.value" in block
    assert "ConversionJob.scheduled_at <= datetime.utcnow()" in block
    assert ".order_by(asc(ConversionJob.priority), asc(ConversionJob.created_at))" in block


def test_stale_requeue_index_is_present_in_migrations() -> None:
    repo_root = _find_repo_root(Path(__file__))
    versions_dir = repo_root / "migrations" / "versions"
    assert versions_dir.is_dir()

    needle = "ix_meta_conversion_jobs_stale"
    found = False
    for path in sorted(versions_dir.glob("*.py")):
        text = _read(path)
        if needle in text and "create_index" in text and "meta_conversion_jobs" in text:
            found = True
            break
    assert found, f"Missing migrations coverage for stale job index: {needle}"
