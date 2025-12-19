import sys
import os
import uuid

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from yuantus.database import SessionLocal
from yuantus.meta_engine.workflow.service import WorkflowService
from yuantus.meta_engine.workflow.models import (
    WorkflowTask,
    WorkflowActivityInstance,
)
from yuantus.security.rbac.models import RBACUser, RBACRole
from yuantus.meta_engine.models.item import Item


def run_workflow_test():
    session = SessionLocal()
    svc = WorkflowService(session)

    print("=== Workflow Service Verification ===")

    try:
        # 1. Setup Data
        # Assume Seed Data exists (ECO Workflow, Administrator Role)
        admin_role = session.query(RBACRole).filter_by(name="Administrator").first()
        admin_users = (
            session.query(RBACUser)
            .join(RBACUser.roles)
            .filter(RBACRole.id == admin_role.id)
            .all()
        )

        if not admin_users:
            print("[FAIL] No Admin users found to assign tasks to.")
            return

        admin_user_id = admin_users[0].id  # Use PK
        print(
            f"> Found Administrator: User PK {admin_user_id}, User ID {admin_users[0].user_id}"
        )

        # Mock Item ID
        # Create a real item in 'In Review' state to test auto-promotion
        # We need "state_review" ID from seed
        state_review_id = "state_review"

        item = Item(
            id=str(uuid.uuid4()),
            item_type_id="Part",
            config_id=str(uuid.uuid4()),
            state="In Review",
            current_state=state_review_id,
            permission_id="perm_part_released",
            is_current=True,
            generation=1,
        )
        session.add(item)
        session.flush()
        item_id = item.id
        print(f"> Created Dummy Item: {item_id} (State: {item.state})")

        # 2. Start Workflow
        print(f"> Starting 'ECO Workflow' for Item {item_id}...")
        process = svc.start_workflow(item_id, "ECO Workflow", admin_user_id)
        session.commit()

        print(f"  Process Started: {process.id}, State: {process.state}")

        # 3. Verify Start Activity (Auto-transition to Review?)
        # My seed logic had Start -> Review (Default).
        # Start activity is type='start', verify if service auto-advanced it.
        # Check active instance
        active_instances = (
            session.query(WorkflowActivityInstance)
            .filter_by(process_id=process.id, state="Active")
            .all()
        )

        current_act = active_instances[0]
        print(f"  Current Activity: {current_act.activity.name}")

        if current_act.activity.name != "Manager Review":
            print(
                f"[FAIL] Expected 'Manager Review', got '{current_act.activity.name}'"
            )
            # If it remained at 'Start', check why auto-advance didn't happen
            return

        # 4. Verify Task Creation
        tasks = (
            session.query(WorkflowTask)
            .filter_by(activity_instance_id=current_act.id, status="Pending")
            .all()
        )

        print(f"  Generated {len(tasks)} tasks.")
        if len(tasks) == 0:
            print("[FAIL] No tasks generated for Review.")
            return

        task = tasks[0]
        print(f"  Task ID: {task.id}, Assigned To: {task.assigned_to_user_id}")

        # 5. Vote
        print("> Voting 'Approve'...")
        svc.vote(task.id, "Approve", admin_user_id, "Looks good to me.")
        session.commit()

        # 6. Verify Transition to End
        # Reload Process
        session.refresh(process)
        print(f"  Process State: {process.state}")

        if process.state == "Completed":
            print("[PASS] Workflow Completed Successfully.")

            # Verify Item Promotion
            session.refresh(item)
            print(f"  Item Final State: {item.state}")
            if item.state == "Released":
                print("[PASS] Lifecycle Auto-Promotion Verified!")
            else:
                print(
                    f"[FAIL] Item not promoted. Expected 'Released', got '{item.state}'"
                )
        else:
            # Check current activity
            active_instances = (
                session.query(WorkflowActivityInstance)
                .filter_by(process_id=process.id, state="Active")
                .all()
            )
            if active_instances:
                print(f"[FAIL] Workflow stuck at: {active_instances[0].activity.name}")
            else:
                print(
                    f"[FAIL] Workflow state is {process.state} but no active instances."
                )

    except Exception as e:
        print(f"[CRASH] {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_workflow_test()
