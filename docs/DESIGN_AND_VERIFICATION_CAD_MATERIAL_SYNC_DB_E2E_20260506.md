# CAD Material Sync DB E2E Design And Verification

## Goal

补齐 macOS 上能执行的最强端到端验证：用 CAD mock drawing fixture 抽取字段，调用 Yuantus `yuantus-cad-material-sync` 插件，在真实 SQLite 数据库中 dry-run、创建、更新 PLM Item，再通过 outbound 字段包回填 CAD fixture。

这个切片不替代 Windows + AutoCAD 真实 DWG smoke，但可以验证服务端插件、数据库写入路径、AML Engine 和 CAD 字段回填契约。

## Design

新增两层验证：

- Yuantus pytest：`src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py`
  - 使用真实 SQLAlchemy SQLite in-memory DB。
  - 创建最小 `Part` ItemType。
  - 通过 FastAPI `TestClient` 调用插件路由。
  - 覆盖 dry-run 不落库、真实 create、真实 update、outbound 字段包。
- AutoCAD 客户端脚本：`clients/autocad-material-sync/verify_material_sync_db_e2e.py`
  - 读取 `fixtures/material_sync_mock_drawing.json`。
  - 复用 `verify_material_sync_fixture.py` 的字段抽取和回填规则。
  - 自动定位当前 Yuantus 仓库根目录，也支持 `YUANTUS_ROOT=/path/to/Yuantus`。
  - 用真实 SQLite DB 和 Yuantus 插件路由执行 create/update/outbound。

数据库表只创建当前路径需要的最小集合，避免 `Base.metadata.create_all()` 被无关模型外键阻塞。创建表包括 `ItemType`、`Property`、`Item`、`ItemVersion`、RBAC、Permission、Lifecycle 和 WorkflowMap 的最小依赖表。

## Covered Flow

1. 从 CAD fixture 抽取 `图号`、`名称`、`材料`、`物料类别`、`长`、`宽`、`厚`。
2. 调用 `/sync/inbound` dry-run，确认 `action=created`，不创建 DB Item，并合成 `specification=1200*600*12`。
3. 调用 `/sync/inbound` 真实创建，确认创建 `Part` Item 并写入物料属性。
4. 调用 `/sync/inbound` 真实更新，用 `overwrite=true` 将材料从 `Q235B` 更新为 `Q355B`。
5. 调用 `/sync/outbound`，确认返回 `材料=Q355B` 和 `规格=1200*600*12` 的 CAD 字段包。
6. 将 outbound `cad_fields` 回填 CAD fixture，确认块属性、表格材料和规格字段更新。

## Verification

Yuantus 插件测试：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```

结果：

```text
11 passed, 1 warning in 0.70s
```

AutoCAD 客户端 DB e2e：

```bash
python3 clients/autocad-material-sync/verify_material_sync_db_e2e.py
```

结果：

```text
OK: material sync SQLite DB create/update/outbound e2e passed
```

warning 为本机 Python/urllib3 的 LibreSSL 兼容提示，不是本功能失败。

## Remaining Boundary

仍需 Windows + AutoCAD 2018 环境优先验证，AutoCAD 2024 作为高版本回归。2018 兼容性计划见 `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_AUTOCAD2018_COMPATIBILITY_20260506.md`：

- 编译 `CADDedupPlugin.dll`。
- 在 AutoCAD 加载插件。
- 执行 `PLMMATPROFILES`、`PLMMATCOMPOSE`、`PLMMATPUSH`、`PLMMATPULL`。
- 使用真实 DWG 验证标题栏块属性和明细表回填。
