# 模拟 FastAPI 客户端逻辑，直接调用 Engine 进行集成测试
# 不走 HTTP 网络层，直接测 Service 层逻辑，更快更准

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from yuantus.config.settings import settings
from yuantus.meta_engine.services.engine import AMLEngine
from yuantus.meta_engine.schemas.aml import GenericItem, AMLAction
from yuantus.meta_engine.web.ui_router import _select_mapping
from yuantus.meta_engine.views.mapping import ViewMapping

# Ensure all models are imported to avoid registry errors

# Setup DB
DB_URL = settings.DATABASE_URL
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_verification():
    session = SessionLocal()
    print("\n[VERIFICATION START] ==================================")
    try:
        # ==========================================
        # 场景 A: 工程师创建 Part (Engineer Persona)
        # ==========================================
        print("\n[Case A] Engineer creating Part...")
        # 模拟 User Context: user1 is an engineer (ID=2)
        # identity_id passed to Engine is usually the user_id (int) or username (str) depending on implementation
        # Here we assume Engine expects the string ID or int ID to match RBACUser.user_id
        engine_svc = AMLEngine(session, identity_id=2, roles=["engineer", "user1"])

        req_add = GenericItem(
            type="Part",
            action=AMLAction.add,
            properties={"cost": 50.0},  # 不填 item_number
        )

        # 执行 Add
        res_add = engine_svc.apply(req_add)
        new_id = res_add["id"]
        session.commit()  # 必须提交，否则后续查询看不到

        # 验证 1: 自动编号 Hook 是否生效？
        # 重新查出来
        part_created = engine_svc.apply(
            GenericItem(type="Part", action=AMLAction.get, id=new_id)
        )
        item_data = part_created["items"][0]
        item_props = item_data["properties"]

        print(f"  > Created Item ID: {new_id}")
        print(f"  > Auto-Number Result: {item_props.get('item_number')}")

        if not item_props.get("item_number", "").startswith("P-"):
            print("  [FAIL] Auto-number hook NOT triggered.")
        else:
            print("  [PASS] Auto-number hook triggered successfully.")

        # 验证 2: Lifecycle 状态
        print(f"  > Initial State: {item_data['state']}")
        if item_data["state"] != "Draft":
            print("  [FAIL] Lifecycle attach failed.")
        else:
            print("  [PASS] Lifecycle attached. State is Draft.")

        # ==========================================
        # 场景 B: 视图映射 (View Mapping)
        # ==========================================
        print("\n[Case B] Testing View Mapping...")
        # 直接调用 View Mapping 逻辑
        mappings = (
            session.query(ViewMapping)
            .filter_by(item_type_id="Part")
            .order_by(ViewMapping.sort_order.desc())
            .all()
        )

        map_eng = _select_mapping(
            mappings, identity_id="engineer", device_type="desktop"
        )
        print(f"  > Engineer maps to Form: {map_eng.form_id if map_eng else 'None'}")

        map_vendor = _select_mapping(
            mappings, identity_id="vendor", device_type="desktop"
        )
        print(
            f"  > Vendor maps to Form: {map_vendor.form_id if map_vendor else 'None'}"
        )

        if map_eng.form_id == "form_eng" and map_vendor.form_id == "form_vendor":
            print("  [PASS] View Mapping logic is correct.")
        else:
            print(
                f"  [FAIL] View Mapping logic error. Eng={map_eng.form_id}, Vendor={map_vendor.form_id}"
            )

        # ==========================================
        # 场景 C: 权限护栏 (Security)
        # ==========================================
        print("\n[Case C] Testing Security...")

        # 1. Promote to In Review (Valid for Engineer)
        print("  > Promoting to 'In Review'...")
        try:
            req_promote = GenericItem(
                id=new_id,
                type="Part",
                action=AMLAction.promote,
                properties={"target_state": "In Review"},
            )
            engine_svc.apply(req_promote)
            session.commit()
            print("  [PASS] Promotion successful.")
        except Exception as e:
            print(f"  [FAIL] Promotion failed: {e}")

        # 2. Try to Update (Should Fail)
        print("  > Attempting update on 'In Review' item (Expect 403)...")
        try:
            req_update = GenericItem(
                id=new_id,
                type="Part",
                action=AMLAction.update,
                properties={"cost": 999.0},
            )
            engine_svc.apply(req_update)
            print("  [FAIL] Security hole! Update should be denied.")
        except Exception as e:
            msg = str(e)
            if "Permission denied" in msg or "403" in msg:
                print(f"  [PASS] Update denied correctly: {msg}")
            else:
                print(f"  [FAIL] Unexpected error: {e}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Test crashed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()
        print("\n[VERIFICATION END] ==================================")


if __name__ == "__main__":
    run_verification()
