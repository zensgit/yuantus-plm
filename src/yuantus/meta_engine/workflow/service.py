import uuid
from sqlalchemy.orm import Session
from datetime import datetime

from .models import (
    WorkflowMap,
    WorkflowActivity,
    WorkflowTransition,
    WorkflowProcess,
    WorkflowActivityInstance,
    WorkflowTask,
)
from yuantus.security.rbac.models import RBACUser


class WorkflowService:
    def __init__(self, session: Session):
        self.session = session

    def start_workflow(
        self, item_id: str, map_name: str, user_id: int
    ) -> WorkflowProcess:
        """Start a new workflow process for an item"""
        # 1. Find the Map
        wf_map = self.session.query(WorkflowMap).filter_by(name=map_name).first()
        if not wf_map:
            raise ValueError(f"Workflow Map '{map_name}' not found.")

        # 2. Check if active process already exists
        existing = (
            self.session.query(WorkflowProcess)
            .filter_by(item_id=item_id, state="Active")
            .first()
        )
        if existing:
            raise ValueError(f"Item {item_id} already has an active workflow.")

        # 3. Create Process
        process = WorkflowProcess(
            id=str(uuid.uuid4()),
            workflow_map_id=wf_map.id,
            item_id=item_id,
            state="Active",
        )
        self.session.add(process)

        # 4. Find Start Activity
        start_activity = (
            self.session.query(WorkflowActivity)
            .filter_by(
                workflow_map_id=wf_map.id,
                type="start",  # Assuming explicit 'start' type, or fallback to first?
            )
            .first()
        )

        if not start_activity:
            # Fallback: Find activity with no incoming transitions
            # For now, just raise error
            raise ValueError("No Start Activity defined in Map.")

        # 5. Activate Start Activity
        self._activate_activity(process, start_activity)

        return process

    def is_process_owner(self, process_id: str, user_id: int) -> bool:
        """
        Check if user is the 'owner' of the process (usually Item Creator or Owner).
        ADR-003 Implementation.
        """
        process = self.session.get(WorkflowProcess, process_id)
        if not process:
            return False

        # Avoid circular import if possible, or import locally
        from yuantus.meta_engine.models.item import Item

        item = self.session.get(Item, process.item_id)
        if not item:
            return False

        if item.owner_id and item.owner_id == user_id:
            return True
        if item.created_by_id == user_id:
            return True

        return False

    def vote(
        self, task_id: str, outcome: str, user_id: int, comment: str = None
    ) -> bool:
        """
        User performs a vote on a task.
        Returns True if vote processed, False if error.
        """
        task = self.session.get(WorkflowTask, task_id)
        if not task:
            raise ValueError("Task not found.")

        if task.status != "Pending":
            raise ValueError("Task is already completed.")

        # Verify Assignment
        # 1. Direct User Assignment
        if task.assigned_to_user_id:
            if task.assigned_to_user_id != user_id:
                raise ValueError("User not assigned to this task.")

        # 2. Role Assignment (Group Task)
        elif task.assigned_to_role_id:
            user = self.session.get(RBACUser, user_id)
            if not user:
                raise ValueError("User not found.")

            # Check if user has this role
            # Assuming user.roles is a list of RBACRole objects
            role_ids = [r.id for r in user.roles]
            if task.assigned_to_role_id not in role_ids:
                raise ValueError(
                    f"User does not have required role ID {task.assigned_to_role_id}."
                )

        # 3. Dynamic snapshot (Task was assigned dynamically, effectively mapped to user or role above)
        # If both are null (shouldn't happen in valid state), deny.
        elif not task.assigned_to_user_id and not task.assigned_to_role_id:
            raise ValueError("Task has no valid assignment.")

        # Update Task
        task.outcome = outcome
        task.comment = comment
        task.status = "Completed"
        task.completed_at = datetime.utcnow()
        # If this was a group task, whoever claimed it essentially 'wins' it for now.
        # Ideally we might mark 'claimed_by_id'
        task.assigned_to_user_id = user_id  # Lock it to the completer

        self.session.flush()

        # Evaluate Activity
        self._evaluate_activity(instance=task.activity_instance)

        return True

    def get_pending_tasks(self, user_id: int) -> list[dict]:
        """
        Get all pending tasks for a user (Direct + Role-based).
        """
        user = self.session.get(RBACUser, user_id)
        if not user:
            return []

        role_ids = [r.id for r in user.roles]

        # Query 1: Direct Assignment
        query = self.session.query(WorkflowTask).filter(
            WorkflowTask.status == "Pending",
            WorkflowTask.assigned_to_user_id == user_id,
        )
        direct_tasks = query.all()

        # Query 2: Role Assignment
        role_tasks = []
        if role_ids:
            query_roles = self.session.query(WorkflowTask).filter(
                WorkflowTask.status == "Pending",
                WorkflowTask.assigned_to_role_id.in_(role_ids),
            )
            role_tasks = query_roles.all()

        # Merge and Format
        all_tasks = set(direct_tasks + role_tasks)

        # Import Item model for type lookup
        from yuantus.meta_engine.models.item import Item

        results = []
        for t in all_tasks:
            # Fetch context
            act_inst = t.activity_instance
            process = act_inst.process
            # Fetch Item info with actual type
            item = self.session.get(Item, process.item_id)
            item_info = {
                "id": process.item_id,
                "type": item.item_type_id if item else "Unknown",
            }

            results.append(
                {
                    "id": t.id,
                    "activity": act_inst.activity.name,
                    "process_state": process.state,
                    "item": item_info,
                    "created_at": t.activity_instance.created_at.isoformat(),
                    "instructions": (
                        act_inst.activity.description
                        if hasattr(act_inst.activity, "description")
                        else ""
                    ),
                }
            )

        return results

    def _activate_activity(self, process: WorkflowProcess, activity: WorkflowActivity):
        """Activate a new activity instance and generate tasks"""
        instance = WorkflowActivityInstance(
            id=str(uuid.uuid4()),
            process_id=process.id,
            activity_id=activity.id,
            state="Active",
        )
        self.session.add(instance)
        self.session.flush()

        # Handle Start/End/Auto nodes first
        if activity.type == "start":
            self._evaluate_activity(instance, force_outcome="Default")
            return
        elif activity.type == "end":
            self._close_process(process)
            return

        # Check for orphan (no assignment config)
        if not activity.assignee_type:
            # Backward compat / Fallback
            pass

        tasks_created = False

        # Strategy 1: Dynamic Identity
        if activity.assignee_type == "dynamic":
            from yuantus.meta_engine.models.item import Item

            item = self.session.get(Item, process.item_id)
            target_user_id = None

            if activity.dynamic_identity == "Creator":
                target_user_id = item.created_by_id
            elif activity.dynamic_identity == "Owner":
                target_user_id = item.owner_id
            # elif activity.dynamic_identity == "Manager": ...

            if target_user_id:
                task = WorkflowTask(
                    id=str(uuid.uuid4()),
                    activity_instance_id=instance.id,
                    assigned_to_user_id=target_user_id,
                    dynamic_identity=activity.dynamic_identity,
                    assignee_type="dynamic",
                    status="Pending",
                )
                self.session.add(task)
                tasks_created = True
            else:
                print(
                    f"Warning: Dynamic identity {activity.dynamic_identity} resolved to None for Item {item.id}"
                )

        # Strategy 2: Direct User
        elif activity.assignee_type == "user" and activity.user_id:
            task = WorkflowTask(
                id=str(uuid.uuid4()),
                activity_instance_id=instance.id,
                assigned_to_user_id=activity.user_id,
                assignee_type="user",
                status="Pending",
            )
            self.session.add(task)
            tasks_created = True

        # Strategy 3: Role (Group Task) - DEFAULT
        # Default to 'role' if type is 'role' OR valid role_id is present (legacy)
        elif (
            activity.assignee_type == "role" or not activity.assignee_type
        ) and activity.role_id:
            # Create ONE task assigned to the ROLE (Group Assignment)
            # This follows the "Pool Task" pattern where anyone in the role can see it.
            # The 'vote' method handles validation.
            task = WorkflowTask(
                id=str(uuid.uuid4()),
                activity_instance_id=instance.id,
                assigned_to_role_id=activity.role_id,
                assignee_type="role",
                status="Pending",
            )
            self.session.add(task)
            tasks_created = True

        if not tasks_created:
            print(
                f"Warning: Activity {activity.name} (Type: {activity.type}) has no valid assignees."
            )

    def _evaluate_activity(
        self, instance: WorkflowActivityInstance, force_outcome: str = None
    ):
        """Check voting results and transition"""
        activity = instance.activity

        # 1. Determine Outcome
        final_outcome = None

        if force_outcome:
            final_outcome = force_outcome
        else:
            # Check tasks
            # Logic: If any task pending -> Wait (Conservative)
            # Unless "First Action Wins" ?
            # Implementing "unanimous" for now: All must complete.
            pending_count = (
                self.session.query(WorkflowTask)
                .filter_by(activity_instance_id=instance.id, status="Pending")
                .count()
            )

            if pending_count > 0:
                return  # Still waiting for votes

            # All tasks done. Tally votes.
            # Simplified: Take the majority vote, or just the first one if conflict.
            # Let's assume the first non-null outcome.
            # (Real engine needs complex Weighted Voting rules)
            tasks = instance.tasks
            outcomes = [t.outcome for t in tasks if t.outcome]
            if outcomes:
                final_outcome = outcomes[0]  # Very simple logic
            else:
                final_outcome = "Default"

        # 2. Find Transition
        # Match transition.condition == final_outcome
        transition = (
            self.session.query(WorkflowTransition)
            .filter_by(from_activity_id=activity.id, condition=final_outcome)
            .first()
        )

        if not transition:
            # Try finding a "Default" path if specific outcome not matched
            transition = (
                self.session.query(WorkflowTransition)
                .filter_by(from_activity_id=activity.id, condition="Default")
                .first()
            )

        if not transition:
            # Dead end?
            print(
                f"Error: No transition found from {activity.name} for outcome {final_outcome}"
            )
            return

        # 3. Close Current Instance
        instance.state = "Completed"
        instance.closed_at = datetime.utcnow()

        # 4. Activate Next
        next_activity = transition.to_activity
        self._activate_activity(instance.process, next_activity)

    def _close_process(self, process: WorkflowProcess):
        process.state = "Completed"
        process.closed_at = datetime.utcnow()

        # Trigger Lifecycle Promotion (Phase 2.5 Integration)
        # Logic: If Workflow ends successfully, try to promote the Item to the next state.
        try:
            from yuantus.meta_engine.lifecycle.service import LifecycleService
            from yuantus.meta_engine.models.item import Item
            from yuantus.meta_engine.lifecycle.models import (
                LifecycleTransition,
                LifecycleState,
            )

            item = self.session.get(Item, process.item_id)
            if not item or not item.current_state:
                return

            # Find a transition out of current state
            # Assumption: Workflow completion implies we should move forward.
            transitions = (
                self.session.query(LifecycleTransition)
                .filter(LifecycleTransition.from_state_id == item.current_state)
                .all()
            )

            target_transition = None
            # Heuristic: Pick the transition that leads to a state named 'Released'
            # OR if only one transition exists, take it.
            if len(transitions) == 1:
                target_transition = transitions[0]
            else:
                # Try to find one that goes to "Released"
                for t in transitions:
                    to_state_id = t.to_state_id
                    to_state = self.session.get(LifecycleState, to_state_id)
                    # Check name
                    if to_state and to_state.name == "Released":
                        target_transition = t
                        break

            if target_transition:
                to_state = self.session.get(
                    LifecycleState, target_transition.to_state_id
                )
                lc_svc = LifecycleService(self.session)

                # Perform Promotion as System (Administrator)
                from yuantus.security.rbac.models import RBACUser

                admin_user = (
                    self.session.query(RBACUser).filter_by(username="admin").first()
                )
                if not admin_user:
                    print("Error: 'admin' user not found for auto-promotion.")
                    return

                system_user_id = admin_user.id

                print(
                    f"Workflow Complete: Promoting Item {item.id} to {to_state.name} by User PK {system_user_id}..."
                )
                promo_res = lc_svc.promote(
                    item=item,
                    target_state_name=to_state.name,
                    user_id=system_user_id,
                    comment="Automatic promotion by Workflow Completion",
                )
                if not promo_res.success:
                    print(f"Auto-promotion failed: {promo_res.error}")
                else:
                    print(f"Auto-promotion successful: {promo_res.to_state}")

        except Exception as e:
            print(f"Error executing auto-promotion: {e}")
            import traceback

            traceback.print_exc()
