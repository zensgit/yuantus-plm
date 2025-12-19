import sys
import os
import uuid

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from yuantus.database import SessionLocal
from yuantus.meta_engine.business_logic.models import Method
from yuantus.meta_engine.services.method_service import MethodService
from yuantus.meta_engine.models.item import Item


def run_method_test():
    session = SessionLocal()
    svc = MethodService(session)

    print("=== Method Service Verification ===")

    try:
        # 0. Clean old methods
        session.query(Method).filter(Method.name == "test_update_state").delete()

        # 1. Register a Test Method (Script)
        # Type: PYTHON_SCRIPT
        # Logic: Update Item property
        code = """
# Dynamic Script
print(f"Hello from DB! Processing Item {item.id}")
item.state = "UpdatedByMethod"
result = "Success"
"""
        method = Method(
            id=str(uuid.uuid4()),
            name="test_update_state",
            type="python_script",
            content=code,
        )
        session.add(method)
        session.commit()
        print(f"> Registered Method: {method.name}")

        # 2. Create Dummy Item
        item = Item(
            id=str(uuid.uuid4()),
            item_type_id="Part",
            config_id=str(uuid.uuid4()),
            state="Original",
            is_current=True,
            generation=1,
        )
        session.add(item)
        session.flush()

        # 3. Execute Method
        print(f"> Item Before: {item.state}")

        context = {"item": item, "session": session, "user_id": 1}

        ret = svc.execute_method("test_update_state", context)

        print(f"> Method Returned: {ret}")
        print(f"> Item After: {item.state}")

        if item.state == "UpdatedByMethod" and ret == "Success":
            print("[PASS] Method execution successful.")
        else:
            print("[FAIL] Method output mismatch.")

    except Exception as e:
        print(f"[CRASH] {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_method_test()
