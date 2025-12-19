import sys
import os
import uuid

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from yuantus.database import SessionLocal
from yuantus.meta_engine.lifecycle.service import LifecycleService
from yuantus.meta_engine.workflow.models import WorkflowProcess
from yuantus.meta_engine.models.item import Item
from yuantus.security.rbac.models import RBACUser


def run_integration_test():
    session = SessionLocal()
    lc_svc = LifecycleService(session)

    print("=== Integration Test: Lifecycle -> Workflow ===")

    try:
        # 1. Setup Data
        # Get Engineer User
        eng_user = (
            session.query(RBACUser).filter_by(username="user1").first()
        )  # user1 is engineer
        if not eng_user:
            print("[FAIL] Engineer user not found.")
            return

        print(f"> Using Engineer: {eng_user.username} (ID: {eng_user.id})")

        # Create Item (Part) in Draft
        part = Item(
            id=str(uuid.uuid4()),
            item_type_id="Part",
            config_id=str(uuid.uuid4()),
            state="Draft",
            is_current=True,
            generation=1,
            # Need to link to LifecycleMap? It's done via ItemType -> LifecycleMap in Service
            # Seed data has Part -> LC_Part
        )
        # We need to set current_state FK manually or use attach_lifecycle?
        # Use attach_lifecycle
        from yuantus.meta_engine.models.meta_schema import ItemType

        lc_svc.attach_lifecycle(session.get(ItemType, "Part"), part)
        # Simplified: just set state manually matching seed ID
        # Seed: Draft ID = "state_draft"
        part.current_state = "state_draft"

        session.add(part)
        session.flush()
        print(f"> Created Part: {part.id} (State: {part.state})")

        # 2. Promote to "In Review"
        # This requires Engineer Role.
        print("> Promoting to 'In Review'...")
        result = lc_svc.promote(
            item=part,
            target_state_name="In Review",
            user_id=eng_user.id,  # Internal ID
            comment="Submitting for review",
        )

        if not result.success:
            print(f"[FAIL] Promotion failed: {result.error}")
            return

        print(f"  Promote Result: {result.success}, State: {part.state}")

        # 3. Verify Workflow Created
        process = (
            session.query(WorkflowProcess)
            .filter_by(item_id=part.id, state="Active")
            .first()
        )

        if process:
            print(
                f"[PASS] Workflow Triggered: {process.workflow_map.name} (Process ID: {process.id})"
            )
        else:
            print("[FAIL] No active workflow found for item.")

    except Exception as e:
        print(f"[CRASH] {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_integration_test()
