# YuantusPLM 验证结果（实际执行记录）

> 完整复现步骤与更多验证项：见 `docs/VERIFICATION.md`。

## 2026-02-09 Perf CI (PASS) - Generic Gate + PR Perf Triggers

- PR checks (PR #76):
  - `perf-p5-reports` run `21814459187` (success)
  - `perf-roadmap-9-3` run `21814459189` (success)
- PR checks (PR #79, config/baseline refactor):
  - `perf-p5-reports` run `21823036492` (success)
  - `perf-roadmap-9-3` run `21823036504` (success)
- Main runs (workflow_dispatch):
  - `perf-p5-reports` run `21821935491` (success)
  - `perf-roadmap-9-3` run `21821935636` (success)
- Main runs (workflow_dispatch, post-refactor):
  - `perf-p5-reports` run `21832779252` (success)
  - `perf-roadmap-9-3` run `21832780373` (success)
- Notes:
  - Gate script: `scripts/perf_gate.py` (DB-aware; supports per-DB overrides)
  - Gate config: `configs/perf_gate.json` (defaults + profiles + `postgres` overrides)
  - Baseline downloader: `scripts/perf_ci_download_baselines.sh` (best-effort, shared by perf workflows)
  - CI optimization: perf workflows use `concurrency.cancel-in-progress`
  - Postgres thresholds in CI: `pct=0.50`, `abs-ms=15ms` (SQLite unchanged)

## 2026-02-09 Perf (PASS) - Roadmap 9.3 (SQLite + Postgres)

- Reports:
  - `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260209-000914.md`
  - `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_PG_20260209-001013.md`
- Trend: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_TREND.md`
- CI:
  - Workflow: `perf-roadmap-9-3` (workflow_dispatch)
  - Pre-merge run (branch): `21801294326` (success)
  - Post-merge run (main): `21801412881` (success)
  - Artifacts: `perf-roadmap-9-3-report`, `perf-roadmap-9-3-report-pg`, `perf-roadmap-9-3-gate`, `perf-roadmap-9-3-trend`
- Notes:
  - Forced Dedup Vision to SKIP: `YUANTUS_DEDUP_VISION_BASE_URL=http://example.invalid:8100`
  - Postgres provisioned via Docker: `postgres:16` -> `localhost:55432`
- Commands:
  - `docker run -d --name yuantus-roadmap93-pg -e POSTGRES_USER=yuantus -e POSTGRES_PASSWORD=yuantus -e POSTGRES_DB=yuantus_perf -p 55432:5432 postgres:16`
  - `YUANTUS_DEDUP_VISION_BASE_URL=http://example.invalid:8100 python3 scripts/perf_roadmap_9_3.py --out docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260209-000914.md`
  - `YUANTUS_DEDUP_VISION_BASE_URL=http://example.invalid:8100 python3 scripts/perf_roadmap_9_3.py --db-url postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_perf --out docs/PERFORMANCE_REPORTS/ROADMAP_9_3_PG_20260209-001013.md`
  - `python3 scripts/perf_roadmap_9_3_trend.py --out docs/PERFORMANCE_REPORTS/ROADMAP_9_3_TREND.md`

## 2026-02-08 Strict Gate (PASS) - Release Orchestration

- Report: `docs/DAILY_REPORTS/STRICT_GATE_20260208-105603.md`
- Scope: release orchestration plan/execute API + unit tests + Playwright API-only regression

## 2026-02-08 Perf (PASS) - P5 Reports/Search

- Report: `docs/PERFORMANCE_REPORTS/P5_REPORTS_PERF_20260208-211413.md`
- Trend: `docs/PERFORMANCE_REPORTS/P5_REPORTS_PERF_TREND.md`
- Scenarios:
  - Reports summary (p95)
  - Reports advanced search response (p95)
  - Saved search run (p95)
  - Report execute (p95)
  - Report export CSV (p95)
- Commands:
  - `./.venv/bin/python scripts/perf_p5_reports.py`
  - `./.venv/bin/python scripts/perf_p5_reports_trend.py`

## 2026-02-07 Strict Gate (PASS) - Product Detail Cockpit Flags

- Report: `docs/DAILY_REPORTS/STRICT_GATE_20260207-222534.md`
- Scope: product detail cockpit flags (impact/readiness/open ECO links-only integration) + Playwright regression extension

## 2026-02-07 Strict Gate (PASS) - Demo PLM Closed Loop

- Report: `docs/DAILY_REPORTS/STRICT_GATE_20260207-224401.md`
- Demo report: `docs/DAILY_REPORTS/DEMO_PLM_CLOSED_LOOP_20260207-224427.md`
- Scope: closed-loop demo script + strict gate optional demo step (`DEMO_SCRIPT=1`)

## 2026-02-07 Strict Gate (PASS) - Item Cockpit

- Report: `docs/DAILY_REPORTS/STRICT_GATE_20260207-220207.md`
- Scope: item cockpit + export bundle + Playwright API-only coverage

## 2026-02-07 Strict Gate (PASS)

- Report: `docs/DAILY_REPORTS/STRICT_GATE_20260207-164556.md`
- Scope: release readiness + ECO apply diagnostics + ruleset directory

## Run H（全功能验证：Health → AML → File → BOM → ECO → Versions → Plugins）

- 时间：`2025-12-18 22:12:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- AUTH_MODE：`required`
- 说明：按 DEVELOPMENT_PLAN.md 的 DoD 要求，执行完整功能验证链路。

### 1) Health

```bash
curl -s http://127.0.0.1:7910/api/v1/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"ok":true,"service":"yuantus-plm","version":"0.1.0","tenant_id":"tenant-1","org_id":"org-1"}
```

### 2) Seed Meta

```bash
yuantus seed-meta
```

```text
Seeded meta schema: Part, Part BOM
```

### 3) Auth Login

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}'
```

```json
{"access_token":"<redacted>","token_type":"bearer","expires_in":3600,"tenant_id":"tenant-1","user_id":1}
```

后续命令需要 `$TOKEN`，可用下面方式提取：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

### 4) Meta：读取 Part 字段定义

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/metadata/Part \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"id":"Part","label":"Part","is_relationship":false,"properties":[{"name":"item_number","label":"Part Number","type":"string","required":true,"length":32,"default":null},{"name":"name","label":"Name","type":"string","required":false,"length":128,"default":null},...]}
```

### 5) AML：创建 Part

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-VERIFY-1766067156","name":"Verify Part 1766067156"}}'
```

```json
{"id":"13e689dd-7470-42a8-a472-df8b1618cd41","type":"Part","status":"created"}
```

### 6) AML：查询 Part

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"get"}'
```

```text
count=6, items=6
```

### 7) Search

```bash
curl -s 'http://127.0.0.1:7910/api/v1/search/?q=Part&item_type=Part' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
total=6, hits=6
```

### 8) RPC：Item.create

```bash
curl -s http://127.0.0.1:7910/api/v1/rpc/ \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"model":"Item","method":"create","args":[{"type":"Part","properties":{"item_number":"P-RPC-1766067162","name":"RPC Part"}}],"kwargs":{}}'
```

```json
{"result":{"id":"2699c82c-ce83-43fe-84df-725adc055958","type":"Part","status":"created"}}
```

### 9) File：上传

```bash
echo "yuantus verification test $(date)" > /tmp/yuantus_verify_test.txt
```

```bash
curl -s 'http://127.0.0.1:7910/api/v1/file/upload?generate_preview=false' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F 'file=@/tmp/yuantus_verify_test.txt'
```

```json
{"id":"ab0a5a06-2255-498d-bd91-83567831e690","filename":"yuantus_verify_test.txt","url":"/api/v1/file/ab0a5a06-2255-498d-bd91-83567831e690/download","size":55,"mime_type":"text/plain","is_cad":false,"preview_url":null}
```

### 10) File：元数据 + 下载

```bash
curl -s http://127.0.0.1:7910/api/v1/file/ab0a5a06-2255-498d-bd91-83567831e690 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"id":"ab0a5a06-2255-498d-bd91-83567831e690","filename":"yuantus_verify_test.txt","file_type":"txt","mime_type":"text/plain","file_size":55,"checksum":"e0ce9cadf250fbbe449d2441b47254d740867b10c1214863ccb23eef1cb21f9f","document_type":"other","is_native_cad":false}
```

```bash
curl -s -o /tmp/yuantus_downloaded.txt -w '%{http_code}\n' \
  http://127.0.0.1:7910/api/v1/file/ab0a5a06-2255-498d-bd91-83567831e690/download \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
HTTP_CODE=200
Content: yuantus verification test Thu Dec 18 22:13:01 CST 2025
```

### 11) BOM：查询有效 BOM

```bash
curl -s http://127.0.0.1:7910/api/v1/bom/13e689dd-7470-42a8-a472-df8b1618cd41/effective \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"id":"13e689dd-7470-42a8-a472-df8b1618cd41","item_type_id":"Part","generation":1,"is_current":true,"state":"New","item_number":"P-VERIFY-1766067156","name":"Verify Part 1766067156","children":[]}
```

### 12) Plugins

```bash
curl -s http://127.0.0.1:7910/api/v1/plugins \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
ok=True, plugins=1
```

```bash
curl -s http://127.0.0.1:7910/api/v1/plugins/demo/ping \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"ok":true,"plugin":"yuantus-demo"}
```

### 13) ECO 完整流程

#### 13.1) 创建 Stage

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/stages' \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"Review","sequence":10,"approval_type":"mandatory","approval_roles":["admin"]}'
```

```json
{"id":"32b7bebb-5347-4283-a400-5299766805b8","name":"Review","sequence":10,"approval_type":"mandatory"}
```

#### 13.2) 创建 ECO

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco' \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"ECO-VERIFY-1766067219","eco_type":"bom","product_id":"13e689dd-7470-42a8-a472-df8b1618cd41","description":"Verification ECO","priority":"normal"}'
```

```json
{"id":"f1901a41-2d67-4ca4-800f-468548a6f4c7","name":"ECO-VERIFY-1766067219","eco_type":"bom","product_id":"13e689dd-7470-42a8-a472-df8b1618cd41","state":"draft","kanban_state":"normal","priority":"normal"}
```

#### 13.3) new-revision

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/f1901a41-2d67-4ca4-800f-468548a6f4c7/new-revision' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"success":true,"version_id":"76de020f-97dd-4cb1-ba5e-ec70146e1a14","version_label":"1.A-eco-f1901a41"}
```

#### 13.4) approve

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/f1901a41-2d67-4ca4-800f-468548a6f4c7/approve' \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"comment":"verification approved"}'
```

```json
{"id":"3461f5ae-2ab7-4d11-9bd0-6e83782e195a","eco_id":"f1901a41-2d67-4ca4-800f-468548a6f4c7","status":"approved","comment":"verification approved"}
```

#### 13.5) apply

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/f1901a41-2d67-4ca4-800f-468548a6f4c7/apply' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"success":true,"message":"ECO applied successfully"}
```

#### 13.6) 验证 current_version_id 已切换

```bash
curl -s http://127.0.0.1:7910/api/v1/bom/13e689dd-7470-42a8-a472-df8b1618cd41/effective \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
current_version_id=76de020f-97dd-4cb1-ba5e-ec70146e1a14
```

#### 13.7) Kanban

```bash
curl -s 'http://127.0.0.1:7910/api/v1/eco/kanban' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"stages":[{"id":"32b7bebb-5347-4283-a400-5299766805b8","name":"Review","sequence":10}],"ecos_by_stage":{"32b7bebb-5347-4283-a400-5299766805b8":[{"id":"f1901a41-2d67-4ca4-800f-468548a6f4c7","name":"ECO-VERIFY-1766067219","state":"done","kanban_state":"done"}]}}
```

### 14) Versions：历史 + 树

```bash
curl -s http://127.0.0.1:7910/api/v1/versions/items/13e689dd-7470-42a8-a472-df8b1618cd41/history \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
[{"id":"30ae8bc2-6f57-46e9-bb3e-edb3ec4fa47f","version_id":"76de020f-97dd-4cb1-ba5e-ec70146e1a14","action":"branch","comment":"Branched 'eco-f1901a41' from 1.A"},{"id":"99525151-f0ac-4f0f-9c25-b75f41f5b417","version_id":"d197d7c7-33b9-4279-8474-bb914588db46","action":"create","comment":"Initial version created"}]
```

```bash
curl -s http://127.0.0.1:7910/api/v1/versions/items/13e689dd-7470-42a8-a472-df8b1618cd41/tree \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
[{"id":"d197d7c7-33b9-4279-8474-bb914588db46","label":"1.A","predecessor_id":null,"branch":"main","state":"Draft"},{"id":"76de020f-97dd-4cb1-ba5e-ec70146e1a14","label":"1.A-eco-f1901a41","predecessor_id":"d197d7c7-33b9-4279-8474-bb914588db46","branch":"eco-f1901a41","state":"Draft"}]
```

### 15) Integrations Health

```bash
curl -s 'http://127.0.0.1:7910/api/v1/integrations/health' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
ok=False, services: athena=False, cad_ml=False, dedup_vision=False
```

> 说明：外部服务未启动是预期的，接口本身稳定返回。

### 验证汇总

| 验证项 | 结果 | 说明 |
|--------|------|------|
| Health | ✅ | 服务存活 |
| Auth Login | ✅ | JWT 签发正常 |
| AML add/get | ✅ | Part 创建/查询正常 |
| Search | ✅ | DB fallback 正常 |
| RPC Item.create | ✅ | 统一 RPC 正常 |
| File upload/download | ✅ | 文件上传/下载正常 |
| BOM effective | ✅ | BOM 查询正常 |
| Plugins | ✅ | 插件系统正常 |
| ECO 完整流程 | ✅ | create → new-revision → approve → apply |
| Versions history/tree | ✅ | 版本历史/树正常 |
| Integrations | ⚠️ | 外部服务未启动（预期） |

---

## Run G（CAD Import Pipeline：`POST /api/v1/cad/import` + `cad_preview`）

- 时间：`2025-12-18 21:48:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`35192`（见 `yuantus.pid`）
- 说明：验证 CAD 导入接口入库 + 创建后台任务 + Worker 执行 `cad_preview` 生成预览，并可通过 `/api/v1/file/{file_id}/preview` 获取 PNG。

### 1) Seed identity + 登录获取 Token

```bash
.venv/bin/yuantus seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin
TOKEN='<redacted>'
```

### 2) 准备一个 dummy CAD 文件（DWG）

```bash
TEST_FILE=/tmp/yuantus_cad_import_test.dwg
echo "dummy dwg $(date)" > "$TEST_FILE"
```

### 3) CAD 导入（仅创建预览任务）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@$TEST_FILE" \
  -F 'create_preview_job=true' \
  -F 'create_geometry_job=false' \
  -F 'create_dedup_job=false' \
  -F 'create_ml_job=false'
```

```json
{
  "file_id": "a98e2543-29da-4c52-8b49-eb2897242af3",
  "filename": "yuantus_cad_import_test.dwg",
  "checksum": "2839b5287e7bb63c30d70c4d22179fc5b1c70864fea73ac35a76176c2b43b4c1",
  "is_duplicate": false,
  "item_id": null,
  "attachment_id": null,
  "jobs": [
    {
      "id": "a8dc9037-e5cb-45fa-a9ef-3dd2743462c0",
      "task_type": "cad_preview",
      "status": "pending"
    }
  ],
  "download_url": "/api/v1/file/a98e2543-29da-4c52-8b49-eb2897242af3/download",
  "preview_url": null,
  "geometry_url": null
}
```

### 4) 运行 Worker 执行一次任务

```bash
.venv/bin/yuantus worker --worker-id worker-cad --poll-interval 1 --once
```

```text
Processed one job.
```

### 5) 查询 Job 结果（completed + payload.result.preview_url）

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/a8dc9037-e5cb-45fa-a9ef-3dd2743462c0 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "a8dc9037-e5cb-45fa-a9ef-3dd2743462c0",
  "task_type": "cad_preview",
  "payload": {
    "file_id": "a98e2543-29da-4c52-8b49-eb2897242af3",
    "result": {
      "ok": true,
      "file_id": "a98e2543-29da-4c52-8b49-eb2897242af3",
      "preview_path": "2d/a9/_yuantus_cad_import_test/yuantus_cad_import_test_preview.png",
      "preview_url": "/api/v1/file/a98e2543-29da-4c52-8b49-eb2897242af3/preview"
    }
  },
  "status": "completed",
  "worker_id": "worker-cad"
}
```

### 6) 获取预览 PNG（HTTP 200）

```bash
curl -s -o /tmp/yuantus_preview_test.png -w '%{http_code}\n' \
  http://127.0.0.1:7910/api/v1/file/a98e2543-29da-4c52-8b49-eb2897242af3/preview \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
file /tmp/yuantus_preview_test.png
```

```text
200
PNG image data, 1 x 1, 8-bit/color RGB, non-interlaced
```

> 说明：当前 dev 环境未安装 Pillow 时，会落到“最小 PNG”（1x1）占位预览；安装 Pillow/FreeCAD 后可得到更真实的预览图。

## Run D（AUTH_MODE=required，Identity Admin + 多组织成员管理）

- 时间：`2025-12-18 14:00:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`88547`（见 `yuantus.pid`）
- 说明：验证 `/api/v1/admin/*`（组织/用户/成员），并用新用户走多组织 token 切换流程。

### 1) Admin：查看 tenant

```bash
ADMIN_TOKEN='<redacted>'
curl -s http://127.0.0.1:7910/api/v1/admin/tenant \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

```json
{"id":"tenant-1","name":"tenant-1","is_active":true,"created_at":"2025-12-18T04:04:33.143134"}
```

### 2) Admin：创建 org-2

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/orgs \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"id":"org-2","name":"Org 2"}'
```

```json
{"id":"org-2","tenant_id":"tenant-1","name":"Org 2","is_active":true,"created_at":"2025-12-18T05:57:41.003230"}
```

### 3) Admin：创建用户 bob

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/users \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"bob","password":"bob","email":"bob@example.com","is_superuser":false}'
```

```json
{"id":2,"tenant_id":"tenant-1","username":"bob","email":"bob@example.com","is_active":true,"is_superuser":false,"created_at":"2025-12-18T05:57:41.026429","updated_at":"2025-12-18T05:57:41.026431"}
```

### 4) Admin：把 bob 加入 org-2（role=engineer）

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/orgs/org-2/members \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"user_id":2,"roles":["engineer"],"is_active":true}'
```

```json
{"tenant_id":"tenant-1","org_id":"org-2","user_id":2,"roles":["engineer"],"is_active":true,"created_at":"2025-12-18T05:57:41.136002"}
```

### 5) bob：多组织 token 切换并调用业务接口

```bash
BOB_TOKEN='<redacted>'
curl -s http://127.0.0.1:7910/api/v1/auth/orgs \
  -H "Authorization: Bearer $BOB_TOKEN"
```

```json
{"tenant_id":"tenant-1","user_id":2,"orgs":[{"id":"org-2","name":"Org 2","is_active":true}]}
```

```bash
BOB_TOKEN='<redacted>'
ORG_TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/jobs \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $ORG_TOKEN"
```

```http
HTTP/1.1 200 OK
```

---

## Run E（AUTH_MODE=required，Meta Permissions / RBAC 生效验证）

- 时间：`2025-12-18 14:06:23 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`96886`（见 `yuantus.pid`）
- 说明：创建权限集 `PartEngineerOnly`，绑定到 `ItemType=Part`，验证 bob(engineer) 可创建，alice(viewer) 被拒绝。

### 1) 创建权限集 `PartEngineerOnly`

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/permissions \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"id":"PartEngineerOnly","name":"Part Engineer Only"}'
```

```json
{"id":"PartEngineerOnly","name":"Part Engineer Only","accesses":[]}
```

### 2) 配置 ACE：engineer（可创建/读/改）+ world（只读）

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/permissions/PartEngineerOnly/accesses \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"identity_id":"engineer","can_create":true,"can_get":true,"can_update":true,"can_delete":false,"can_discover":true}'
```

```json
{"id":"PartEngineerOnly:engineer","permission_id":"PartEngineerOnly","identity_id":"engineer","can_create":true,"can_get":true,"can_update":true,"can_delete":false,"can_discover":true}
```

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/permissions/PartEngineerOnly/accesses \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"identity_id":"world","can_create":false,"can_get":true,"can_update":false,"can_delete":false,"can_discover":true}'
```

```json
{"id":"PartEngineerOnly:world","permission_id":"PartEngineerOnly","identity_id":"world","can_create":false,"can_get":true,"can_update":false,"can_delete":false,"can_discover":true}
```

### 3) 绑定 `Part` 的 permission_id

```bash
ADMIN_TOKEN='<redacted>'
curl -s -X PATCH http://127.0.0.1:7910/api/v1/meta/item-types/Part/permission \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"permission_id":"PartEngineerOnly"}'
```

```json
{"ok":true,"item_type_id":"Part","permission_id":"PartEngineerOnly"}
```

### 4) bob(engineer) 创建 Part（200） / alice(viewer) 创建 Part（403）

```bash
BOB_TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-RBAC-001","name":"RBAC Part"}}'
```

```http
HTTP/1.1 200 OK
```

```bash
ALICE_TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-RBAC-002","name":"RBAC Part 2"}}'
```

```http
HTTP/1.1 403 Forbidden
```

---

## Run F（Org Admin：仅管理本 org 成员）

- 时间：`2025-12-18 14:11:19 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`2173`（见 `yuantus.pid`）
- 说明：验证“非 superuser”的 org admin（membership role=admin）可以管理本 org 成员，但不能做 tenant 级用户/组织管理。

### 1) org-2 admin 列出 org-2 members（200）

```bash
CHARLIE_TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/admin/orgs/org-2/members \
  -H "Authorization: Bearer $CHARLIE_TOKEN"
```

```http
HTTP/1.1 200 OK
```

### 2) org-2 admin 创建用户（403，Superuser required）

```bash
CHARLIE_TOKEN='<redacted>'
curl -s -i -X POST http://127.0.0.1:7910/api/v1/admin/users \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $CHARLIE_TOKEN" \
  -d '{"username":"x","password":"x"}'
```

```http
HTTP/1.1 403 Forbidden
```

```json
{"detail":"Superuser required"}
```

### 3) org-2 admin 访问 org-1 members（403，Org admin required）

```bash
CHARLIE_TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/admin/orgs/org-1/members \
  -H "Authorization: Bearer $CHARLIE_TOKEN"
```

```http
HTTP/1.1 403 Forbidden
```

```json
{"detail":"Org admin required"}
```

---

## Run C（AUTH_MODE=required，多组织 Token 切换）

- 时间：`2025-12-18 13:41:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`66178`（见 `yuantus.pid`）
- 说明：本次验证“先 tenant 登录 → 列出 orgs → switch-org 签发含 org_id 的 token → 不传 x-org-id 调用业务接口”。

### 1) Login（不带 org_id，已脱敏）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin"}'
```

```json
{"access_token":"<redacted>","token_type":"bearer","expires_in":3600,"tenant_id":"tenant-1","user_id":1}
```

### 2) Orgs（不传 x-org-id）

```bash
TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/auth/orgs \
  -H "Authorization: Bearer $TOKEN"
```

```http
HTTP/1.1 200 OK
```

```json
{"tenant_id":"tenant-1","user_id":1,"orgs":[{"id":"org-1","name":"org-1","is_active":true}]}
```

## Run AUD-1（Audit Logs 验收）

- 时间：`2025-12-20 14:10:18 +0800`
- 基地址：`http://127.0.0.1:7922`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：`audit_enabled=true`（本地启动服务用于验收）

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7922 tenant-1 org-1
```

输出（摘要）：

```text
OK: Seeded identity
OK: Admin login
OK: Health request logged
Audit logs: OK
OK: Audit logs verified

ALL CHECKS PASSED
```

## Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260212-225211

- 时间：`2026-02-12 22:52:58 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision，worker 用本机 CLI 执行）
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision`
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api`
- 命令：`LOG=/tmp/verify_cad_dedup_relationship_s3_20260212-225211.log; scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 证据：`docs/DEV_AND_VERIFICATION_CAD_DEDUP_RELATIONSHIP_S3_PG_MINIO_20260212.md`
- 原始日志：`/tmp/verify_cad_dedup_relationship_s3_20260212-225211.log`

## Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260212-215323

- 时间：`2026-02-12 21:54:06 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision，worker 用本机 CLI 执行）
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision`
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api`
- 命令：`LOG=/tmp/verify_cad_dedup_relationship_s3_20260212-215323.log; scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 证据：`docs/DEV_AND_VERIFICATION_CAD_DEDUP_RELATIONSHIP_S3_PG_MINIO_20260212.md`
- 原始日志：`/tmp/verify_cad_dedup_relationship_s3_20260212-215323.log`

## Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260212-195201

- 时间：`2026-02-12 19:52:01 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision，worker 用本机 CLI 执行）
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d --build postgres minio api dedup-vision`
- 命令：`scripts/verify_cad_dedup_relationship_s3.sh`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 证据：`docs/DEV_AND_VERIFICATION_CAD_DEDUP_RELATIONSHIP_S3_PG_MINIO_20260212.md`


## Run RUN-CAD-DEDUP-VISION-S3-PG-MINIO-20260212-174112

- 时间：`2026-02-12 17:41:12 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Worker + Dedup Vision，`STORAGE_TYPE=s3`）
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision`
- 命令：`docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api`
- 命令：`LOG=/tmp/verify_cad_dedup_vision_s3_20260212-174112.log; scripts/verify_cad_dedup_vision_s3.sh | tee "$LOG"`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 摘要：
  - baseline upload：`verify_dedup_base.png`（`dedup_index=true`）→ search + index success
  - query upload：`verify_dedup_query.png`（`dedup_index=false`）→ search returned baseline match
  - S3 readback：`302->200`（presigned URL；脚本使用 `curl -L` 自动跟随）
  - Dedup rule：`2057c992-d691-4145-a8dd-47e7745c454c`
  - Baseline：file `a63b0d35-96a5-4c3d-af71-dbb375bf2b46`，job `4c409eca-865e-4bdc-9b85-3e8bd5e7adbc`
  - Query：file `50897b9d-af95-4b91-a8b5-aa9ec9c641f0`，job `ab94f266-6e97-457b-b61f-84e830660c64`
- 证据：`/tmp/verify_cad_dedup_vision_s3_20260212-174112.log`

```text
==> Upload baseline PNG via /cad/import (dedup_index=true)
OK: Baseline file uploaded: a63b0d35-96a5-4c3d-af71-dbb375bf2b46
Baseline dedup job ID: 4c409eca-865e-4bdc-9b85-3e8bd5e7adbc
...
==> Upload query PNG via /cad/import (dedup_index=false)
OK: Query file uploaded: 50897b9d-af95-4b91-a8b5-aa9ec9c641f0
Query dedup job ID: ab94f266-6e97-457b-b61f-84e830660c64
...
ALL CHECKS PASSED
```

## Run CAD-PIPELINE-S3-PG-MINIO-20260212-1702

- 时间：`2026-02-12 17:02:54 +0800`
- 环境：`docker compose -f docker-compose.yml`（Postgres + MinIO + API + Worker，`STORAGE_TYPE=s3`）
- 命令：`YUANTUS_SCHEMA_MODE=migrations DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity YUANTUS_STORAGE_TYPE=s3 YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 YUANTUS_S3_BUCKET_NAME=yuantus YUANTUS_S3_ACCESS_KEY_ID=minioadmin YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 摘要：
  - Preview endpoint：`302`
  - Geometry endpoint：`302`
  - presigned URL follow：`200`

```text
==============================================
S3 CAD Pipeline Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity (admin user)
OK: Identity seeded

==> Seed meta schema
OK: Meta schema seeded

==> Login as admin
OK: Admin login

==> Create test STL file
OK: Created test file: /tmp/yuantus_cad_s3_test.stl

==> Upload STL via /cad/import
OK: File uploaded: ed755836-291a-4de3-bdeb-92695fcdfb1b
Preview job ID: 39c082a6-ed93-4eeb-b697-e376616d57a5
Geometry job ID: 362f8213-1d0b-4d15-9492-c2630c6013ba

==> Run worker to process jobs
OK: Worker executed

==> Check job statuses
Preview job status: completed
Geometry job status: completed

==> Check file metadata
Preview URL: /api/v1/file/ed755836-291a-4de3-bdeb-92695fcdfb1b/preview
Geometry URL: /api/v1/file/ed755836-291a-4de3-bdeb-92695fcdfb1b/geometry
Conversion status: completed
OK: Preview path set
OK: Geometry path set

==> Test preview endpoint
OK: Preview endpoint works (HTTP 302)

==> Test geometry endpoint
OK: Geometry endpoint works (HTTP 302)

==> Check storage type
OK: S3 storage detected (302 redirect)
Testing S3 presigned URL follow (no API auth headers)...
OK: S3 presigned URL accessible (followed redirect)

==> Cleanup
OK: Cleaned up test file

==============================================
CAD Pipeline S3 Verification Complete
==============================================

Summary:
  - File upload: OK
  - Job processing: completed / completed
  - Preview endpoint: 302
  - Geometry endpoint: 302

ALL CHECKS PASSED
```

## Run MT-MIGRATE-AUTOSTAMP-20260112-0915（无 alembic_version 自动 stamp 初始版本）

- 时间：`2026-01-12 09:15:02 +0800`
- 脚本：`scripts/mt_migrate.sh`
- 结果：`Migrations complete`
- 测试 DB：`yuantus_mt_pg__tenant-stamp2__org-stamp2`
- 说明：DB 由 `create_all` 生成且无 `alembic_version`，自动 stamp `f87ce5711ce1` 后顺利 upgrade 到 head。

执行命令：

```bash
MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
TENANTS=tenant-stamp2 ORGS=org-stamp2 \
IDENTITY_DB_URL='' \
AUTO_STAMP_REVISION=f87ce5711ce1 \
  bash scripts/mt_migrate.sh
```

输出（摘要）：

```text
Existing tables without alembic_version; stamping f87ce5711ce1
Running upgrade ... -> m1b2c3d4e6a1
Migrations complete.
```
## Run ALL-13（一键回归脚本：compare_mode + ECO 导出）

- 时间：`2025-12-26 09:17:52 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS=34 / FAIL=0 / SKIP=5`
- 跳过项：
  - S5-C (CAD Auto Part)：`RUN_CAD_AUTO_PART=0`
  - S5-C (CAD Extractor Stub)：`RUN_CAD_EXTRACTOR_STUB=0`
  - S5-C (CAD Extractor External)：`RUN_CAD_EXTRACTOR_EXTERNAL=0`
  - S5-C (CAD Extractor Service)：`RUN_CAD_EXTRACTOR_SERVICE=0`
  - S7 (Tenant Provisioning)：`RUN_TENANT_PROVISIONING=0`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export RUN_CAD_AUTO_PART=0
export RUN_CAD_EXTRACTOR_STUB=0
export RUN_CAD_EXTRACTOR_EXTERNAL=0
export RUN_CAD_EXTRACTOR_SERVICE=0
export RUN_TENANT_PROVISIONING=0

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 34  FAIL: 0  SKIP: 5
ALL TESTS PASSED
```

## Run CAD-MESH-STATS-20260110-2119（mesh-stats 404 守护）

- 时间：`2026-01-10 21:19:00 +0800`
- 方式：直接调用 `get_cad_mesh_stats`（无 HTTP 网络层）
- 结果：`cad_attributes` 返回 404；`cad_mesh` 返回 200 + 统计
- 环境：`sqlite` 临时库 + `local` 存储（`/tmp`）

执行命令（摘要）：

```bash
python3 - <<'PY'
import io, json, os, shutil, uuid

DB_PATH = "/tmp/yuantus_mesh_stats_test.db"
STORAGE_PATH = "/tmp/yuantus_mesh_stats_storage"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
if os.path.exists(STORAGE_PATH):
    shutil.rmtree(STORAGE_PATH)

os.environ["YUANTUS_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["YUANTUS_LOCAL_STORAGE_PATH"] = STORAGE_PATH
os.environ["YUANTUS_SCHEMA_MODE"] = "create_all"

from yuantus.config import get_settings
get_settings.cache_clear()

from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from yuantus.database import create_db_engine, init_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.file_service import FileService
from yuantus.api.dependencies.auth import CurrentUser
from yuantus.meta_engine.web.cad_router import get_cad_mesh_stats

engine = create_db_engine()
init_db(create_tables=True, bind_engine=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

session = SessionLocal()
file_service = FileService()

user = CurrentUser(
    id=1,
    tenant_id="tenant-test",
    org_id="org-test",
    username="tester",
    email=None,
    roles=[],
    is_superuser=False,
)

def create_file_with_metadata(payload):
    file_id = str(uuid.uuid4())
    path = f"cad_metadata/{file_id[:2]}/{file_id}.json"
    file_service.upload_file(io.BytesIO(json.dumps(payload).encode("utf-8")), path)
    file_row = FileContainer(
        id=file_id,
        filename=f"{file_id}.json",
        file_type="json",
        system_path=f"files/{file_id}.json",
        cad_metadata_path=path,
    )
    session.add(file_row)
    session.commit()
    return file_id

attr_id = create_file_with_metadata({"kind": "cad_attributes", "attributes": {"foo": "bar"}})
mesh_id = create_file_with_metadata({"kind": "cad_mesh", "triangle_count": 12, "bounds": [0, 0, 0, 1, 1, 1]})

print("[Case A] cad_attributes payload -> expect 404")
try:
    get_cad_mesh_stats(file_id=attr_id, user=user, db=session)
    print("  [FAIL] Expected 404, got success")
except HTTPException as exc:
    print(f"  [PASS] HTTP {exc.status_code}: {exc.detail}")

print("[Case B] cad_mesh payload -> expect 200")
try:
    resp = get_cad_mesh_stats(file_id=mesh_id, user=user, db=session)
    print(f"  [PASS] stats: {resp.stats}")
except HTTPException as exc:
    print(f"  [FAIL] HTTP {exc.status_code}: {exc.detail}")

session.close()
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
if os.path.exists(STORAGE_PATH):
    shutil.rmtree(STORAGE_PATH)
PY
```

输出（摘要）：

```text
[Case A] cad_attributes payload -> expect 404
  [PASS] HTTP 404: CAD mesh metadata not available
[Case B] cad_mesh payload -> expect 200
  [PASS] stats: {'raw_keys': ['bounds', 'kind', 'triangle_count'], 'triangle_count': 12, 'bounds': [0, 0, 0, 1, 1, 1]}
```

## Run BC-9（BOM Compare：summarized 复验）

- 时间：`2025-12-26 09:15:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`6ed73f5d-d484-4d8a-812f-f3890045a329`
  - Parent B：`42afe6e8-5cd3-4ad3-8be2-65ef4c186de3`
  - Child X：`ebebda5d-56ef-4815-9ddf-37c9c67c2a59`
  - Child Y：`29c5b0e0-0ec3-49a8-8653-232a4517a632`
  - Child Z：`a3fd764d-1b65-49cc-abfa-8a04b79b2e39`
  - Substitute：`421d6162-cb5b-47dd-be6d-4eb7a364adc3`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
BOM Compare only_product: OK
BOM Compare num_qty: OK
BOM Compare summarized: OK
ALL CHECKS PASSED
```

## Run S4-9（ECO Advanced：compare_mode 导出元信息）

- 时间：`2025-12-26 09:15:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_eco_advanced.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Stage：`383084d0-1c27-4490-9cbe-e9ab1a9f5049`
  - Product：`cb0f5d51-326b-40c6-86da-79cfece5e945`
  - Assembly：`bfdcf0f1-d32a-4cd3-9b6e-f8e7de11ac36`
  - ECO1：`6c77c218-ca25-40d1-b508-08217d909b8c`
  - Target Version：`a67cd9fb-45b1-4d93-8529-e5a1101a80dd`
  - ECO2：`e4d7af2a-e68e-489b-9f87-059ed18a137f`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM diff: OK
BOM diff only_product: OK
Impact analysis: OK
Impact export files: OK
Batch approvals (admin): OK
Batch approvals (viewer denied): OK
ALL CHECKS PASSED
```

---

## Run AUD-2（Audit Logs 验收：Docker 运行）

- 时间：`2025-12-20 20:28:23 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：`docker-compose.dev.yml` 绑定本地源码（镜像构建阶段 pip 下载超时）

执行命令：

```bash
YUANTUS_AUDIT_ENABLED=true \
  docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --force-recreate api

DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
OK: Seeded identity
OK: Admin login
OK: Health request logged
Audit logs: OK
OK: Audit logs verified

ALL CHECKS PASSED
```

---

## Run AUD-3（Audit Logs 验收：Docker 镜像 + Wheelhouse）

- 时间：`2025-12-20 23:11:44 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：使用 `requirements.lock` + `vendor/wheels` 进行离线构建

执行命令：

```bash
YUANTUS_AUDIT_ENABLED=true \
  docker compose -p yuantusplm up -d --build api worker

DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
OK: Seeded identity
OK: Admin login
OK: Health request logged
Audit logs: OK
OK: Audit logs verified

ALL CHECKS PASSED
```

---


## S4 ECO Advanced（Impact + BOM Redline + Batch Approvals）

- 时间：`2025-12-19 15:21:26 +0800`
- 基地址：`http://127.0.0.1:7910`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- 命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 关键结果（Run S4-1）

```text
Stage: fb0901f8-130f-49a0-a3db-31dfc7c03070
Product: 7d323729-3163-42ef-a38a-6c82f6be25ab
Assembly: ecafa319-5883-4e89-a135-22710c894d7a
ECO1: 93d5d2d4-f1f7-45fd-a324-b002dac8cf2f
Target Version: 6aaecfdc-cb4e-4775-9b73-360805a66b12
ECO2: 7df1dcd5-ce29-4ee8-a473-2bf7f46a8bea
Result: ALL CHECKS PASSED
```

---

## Run S4-2（ECO Advanced：Impact 分级 + Batch 审计/通知）

- 时间：`2025-12-19 23:16:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- 命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 关键结果（Run S4-2）

```text
Stage: 28159d16-e157-4d4e-85dc-b3e4a8eb07b9
Product: bc407740-d24f-4ef9-bc3a-80d721c5c454
Assembly: 5e798d44-be86-4a37-8d94-c93899997aee
ECO1: e94b355a-f549-462a-bf38-9fc7d9513eb2
Target Version: 2cc0ac7c-a298-4b21-9cbc-e0f1f92fb124
ECO2: 0131cfaa-8a41-4c2d-a017-f8395ad35e5f
Impact level: high
Batch summary: ok=2 failed=0
Result: ALL CHECKS PASSED
```

---

## Run S4-3（ECO Advanced：SLA 通知 + 逾期提醒）

- 时间：`2025-12-19 23:34:51 +0800`
- 基地址：`http://127.0.0.1:7910`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- 命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 关键结果（Run S4-3）

```text
Stage: 0ba05dc0-8974-4571-9b40-2cc49021dcde
Product: 62b8e6db-c840-48b3-b9ca-ba70454016e1
Assembly: bf79c028-4152-4b77-904f-9ba4809d09f1
ECO1: f8f76c3c-18c8-48b2-ac45-67bb6860c3ee
Target Version: a4d7a406-9f59-4625-8ffe-4baf812e9d0d
ECO2: 483406db-b7ed-4970-b74f-be1ca5036bc9
Impact level: high
Overdue list: OK
Overdue notifications: OK
Result: ALL CHECKS PASSED
```

---

## Run ALL-7（一键回归：全部脚本）

- 时间：`2025-12-19 15:27:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- S3：`http://localhost:59000`（MinIO）
- 命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 汇总

```text
PASS: 11  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

---

## S7 Multi-Tenancy（db-per-tenant-org）

- 时间：`2025-12-19 15:44:15 +0800`
- 基地址：`http://127.0.0.1:7912`
- TENANCY_MODE：`db-per-tenant-org`
- DB_URL：`sqlite:///yuantus_mt.db`
- IDENTITY_DB_URL：`sqlite:///yuantus_identity_mt.db`
- 命令：

```bash
DB_URL='sqlite:///yuantus_mt.db' \
IDENTITY_DB_URL='sqlite:///yuantus_identity_mt.db' \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7912 tenant-1 tenant-2 org-1 org-2
```

### 关键结果（Run S7-1）

```text
Org + tenant isolation (A1): OK
Org isolation (A2): OK
Tenant isolation (B1): OK
ALL CHECKS PASSED
```

## Run S7-2（Multi-Tenancy：db-per-tenant-org，SQLite）

- 时间：`2025-12-19 17:08:28 +0800`
- 基地址：`http://127.0.0.1:7912`
- TENANCY_MODE：`db-per-tenant-org`
- DB_URL：`sqlite:///yuantus_mt_run2.db`
- IDENTITY_DB_URL：`sqlite:///yuantus_identity_mt_run2.db`
- 命令：

```bash
# 启动多租户服务（独立端口）
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=sqlite:///yuantus_mt_run2.db \
YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_identity_mt_run2.db \
YUANTUS_SCHEMA_MODE=create_all \
.venv/bin/yuantus start --port 7912 --host 127.0.0.1 &

MODE=db-per-tenant-org \
DB_URL='sqlite:///yuantus_mt_run2.db' \
IDENTITY_DB_URL='sqlite:///yuantus_identity_mt_run2.db' \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7912 tenant-1 tenant-2 org-1 org-2
```

### 关键结果（Run S7-2）

```text
Org + tenant isolation (A1): OK
Org isolation (A2): OK
Tenant isolation (B1): OK
ALL CHECKS PASSED
```

## Run S7-3（Multi-Tenancy：db-per-tenant-org，Postgres 模板）

- 时间：`2025-12-19 17:12:55 +0800`
- 基地址：`http://127.0.0.1:7913`
- TENANCY_MODE：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- 命令：

```bash
# 预创建数据库（tenant/org）
for db in yuantus__tenant-1__org-1 yuantus__tenant-1__org-2 yuantus__tenant-2__org-1; do
  exists=$(docker exec -i yuantusplm-postgres-1 psql -U yuantus -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${db}'")
  if [[ -z "$exists" ]]; then
    docker exec -i yuantusplm-postgres-1 psql -U yuantus -d postgres \
      -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"${db}\";"
  fi
done

# 启动多租户服务（独立端口）
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus__{tenant_id}__{org_id}' \
YUANTUS_SCHEMA_MODE=create_all \
.venv/bin/yuantus start --port 7913 --host 127.0.0.1 &

MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7913 tenant-1 tenant-2 org-1 org-2
```

### 关键结果（Run S7-3）

```text
Org + tenant isolation (A1): OK
Org isolation (A2): OK
Tenant isolation (B1): OK
ALL CHECKS PASSED
```

## Run S7-4（Multi-Tenancy：db-per-tenant-org，SQLite）

- 时间：`2025-12-20 08:40:40 +0800`
- 基地址：`http://127.0.0.1:7912`
- TENANCY_MODE：`db-per-tenant-org`
- DB_URL：`sqlite:///yuantus_mt_run3.db`
- IDENTITY_DB_URL：`sqlite:///yuantus_identity_mt_run3.db`
- 命令：

```bash
# 启动多租户服务（独立端口）
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=sqlite:///yuantus_mt_run3.db \
YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_identity_mt_run3.db \
YUANTUS_SCHEMA_MODE=create_all \
YUANTUS_AUTH_MODE=required \
.venv/bin/yuantus start --port 7912 --host 127.0.0.1 &

MODE=db-per-tenant-org \
DB_URL='sqlite:///yuantus_mt_run3.db' \
IDENTITY_DB_URL='sqlite:///yuantus_identity_mt_run3.db' \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7912 tenant-1 tenant-2 org-1 org-2
```

### 关键结果（Run S7-4）

```text
Org + tenant isolation (A1): OK
Org isolation (A2): OK
Tenant isolation (B1): OK
ALL CHECKS PASSED
```

## Run S6-1（Search Index：增量检索）

- 时间：`2025-12-20 08:51:28 +0800`
- 基地址：`http://127.0.0.1:7911`
- 脚本：`scripts/verify_search_index.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`be1cb779-0d2a-4371-a553-afcdcf7ac87f`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_search_index.sh http://127.0.0.1:7911 tenant-1 org-1
```

输出（摘要）：

```text
Search Index Verification Complete
ALL CHECKS PASSED
```

## Run S6-2（Reports Summary：聚合统计）

- 时间：`2025-12-20 09:09:35 +0800`
- 基地址：`http://127.0.0.1:7914`
- 脚本：`scripts/verify_reports_summary.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`a40bb6a4-00da-480c-9674-e8c21ff854d3`
  - File：`30010e28-9481-4cec-a8aa-247b48cf1c35`
  - ECO：`10764d41-7709-42fd-8a2d-a2d12e245553`
  - Job：`7e574f7a-57b4-46fb-9d77-23f21af73a00`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_reports_summary.sh http://127.0.0.1:7914 tenant-1 org-1
```

输出（摘要）：

```text
Reports Summary Verification Complete
ALL CHECKS PASSED
```

## Run SUB-1（BOM Substitutes 验收）

- 时间：`2025-12-19 13:18:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_substitutes.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent：`378b3b54-716e-4339-b2b5-152d52ecb328`
  - Child：`18e7865d-dea8-4bae-b2e7-36f263a9c82f`
  - Substitute 1：`aaf9fa30-3ee5-4d4c-90fc-ba714ff1aaef`
  - Substitute 2：`46832701-24f7-4bc1-9049-d5eb1c35488c`
  - BOM Line：`4a3d63e3-6212-4211-9bbe-f90c78207674`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_substitutes.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Substitutes Verification Complete
ALL CHECKS PASSED
```

## Run ALL-4（一键回归脚本：verify_all.sh，含 Substitutes）

- 时间：`2025-12-19 13:19:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=9, FAIL=0, SKIP=0)`
- 关键 ID（节选）：
  - Run H Part：`fefbc2ea-13a7-4256-abce-ccf7587af0bf`
  - Run H RPC Part：`407d7bff-4794-4d91-9c8b-b561f408ca2c`
  - Run H File：`1a926443-fcaf-4af3-a2ff-6ef1939ce48f`
  - Run H ECO：`6516a5c6-c944-40cf-926d-e58f67ab836a`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Where-Used Component：`e568d196-8de4-404e-b613-565472b934b9`
  - BOM Compare Parent A：`00b2a2f8-77fc-4569-95bf-8687c1a0a2ac`
  - BOM Substitutes Parent：`158f4742-1415-4136-9f15-3fc7078859f5`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S5-A (CAD Pipeline S3)    PASS
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS

PASS: 9  FAIL: 0  SKIP: 0

ALL TESTS PASSED
```

## Run VF-1（Version-File Binding 验收）

- 时间：`2025-12-19 13:53:42 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_version_files.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`63731a66-3ac9-4df3-93cc-cf9c6315f438`
  - Version：`2d109517-af78-45fd-ba1e-32a3d6571702`
  - File：`50fde1f5-6dec-4c19-8e37-fb7e33981019`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Version files synced: OK
ALL CHECKS PASSED
```

## Run VF-2（Version-File Binding 验收）

- 时间：`2025-12-19 23:43:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_version_files.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`0a91a5f9-8362-4baa-a869-d38b1c5f650c`
  - Version：`950e09bb-37c5-4eae-8c46-3d5ef64fc766`
  - File：`773323cc-355c-49d6-98da-a2fdbfb2b640`

执行命令：

```bash
bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Version files synced: OK
ALL CHECKS PASSED
```

## Run ALL-5（一键回归脚本：verify_all.sh，含 Version-File Binding）

- 时间：`2025-12-19 13:53:42 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=10, FAIL=0, SKIP=0)`
- 关键 ID（节选）：
  - Run H Part：`85fa81ef-8911-4709-a3e6-3b6c58651685`
  - Run H RPC Part：`4e386b97-a454-4959-9cd6-57ffadaec108`
  - Run H File：`d7b091cc-ba63-479c-8f29-eac71f153d80`
  - Run H ECO：`e2b16c6a-5eae-445c-91d2-7b45105ec20a`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Where-Used Component：`a5ea2048-7f5c-4766-814f-af86900f3038`
  - BOM Compare Parent A：`b0079ecc-9bcc-46a2-8458-1501152edb8a`
  - BOM Substitutes Parent：`3e5630ec-2577-4d83-bca3-fa51c8066bfa`
  - Version-File Binding Part：`63731a66-3ac9-4df3-93cc-cf9c6315f438`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S5-A (CAD Pipeline S3)    PASS
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 10  FAIL: 0  SKIP: 0

ALL TESTS PASSED
```

## Run ALL-6（一键回归脚本：verify_all.sh，Docker 重新构建后）

- 时间：`2025-12-19 14:08:14 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=10, FAIL=0, SKIP=0)`
- 关键 ID（节选）：
  - Run H Part：`68c5508e-c24b-49d0-a484-ac123fb1f77a`
  - Run H RPC Part：`f2c0cb54-28ac-4242-b03c-973779b7bd33`
  - Run H File：`b5f4b88a-f502-4da6-ab99-1ccdf20ee760`
  - Run H ECO：`b91e4f56-9672-42f8-b513-c3826b38610f`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Where-Used Component：`9b5a7def-a6bb-48b6-952c-cad71db875e2`
  - BOM Compare Parent A：`2086f297-74d0-4e23-86e4-2d15af0f2ce6`
  - BOM Substitutes Parent：`48b5022f-b9af-403e-9319-9b9dfdf0e75d`
  - Version-File Binding Part：`cb9d859c-451f-4ad9-8760-228bee15eff9`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S5-A (CAD Pipeline S3)    PASS
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 10  FAIL: 0  SKIP: 0

ALL TESTS PASSED
```

容器状态：

```bash
docker compose -p yuantusplm ps
```

```text
NAME                    IMAGE                COMMAND                   SERVICE    CREATED          STATUS                    PORTS
yuantusplm-api-1        yuantusplm-api       "sh -c '\n  echo 'Wai…"   api        11 minutes ago   Up 11 minutes (healthy)   0.0.0.0:7910->7910/tcp, [::]:7910->7910/tcp
yuantusplm-minio-1      minio/minio:latest   "/usr/bin/docker-ent…"    minio      14 hours ago     Up 14 hours (healthy)     0.0.0.0:59000->9000/tcp, [::]:59000->9000/tcp, 0.0.0.0:59001->9001/tcp, [::]:59001->9001/tcp
yuantusplm-postgres-1   postgres:16-alpine   "docker-entrypoint.s…"    postgres   14 hours ago     Up 14 hours (healthy)     0.0.0.0:55432->5432/tcp, [::]:55432->5432/tcp
yuantusplm-redis-1      redis:7-alpine       "docker-entrypoint.s…"    redis      14 hours ago     Up 14 hours               6379/tcp
yuantusplm-worker-2     yuantusplm-worker    "yuantus worker --po…"    worker     11 minutes ago   Up 11 minutes             
```

日志（节选）：

```bash
docker logs --tail 20 yuantusplm-api-1
docker logs --tail 20 yuantusplm-worker-2
```

```text
INFO:     127.0.0.1:46814 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:43648 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:60162 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54182 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54562 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:34316 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44118 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:48370 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:34678 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:47784 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:43802 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33752 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:36582 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:46228 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:33292 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:44262 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:58582 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:42552 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:57860 - "GET /api/v1/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:37796 - "GET /api/v1/health HTTP/1.1" 200 OK
Worker 'worker-1' started. Press Ctrl+C to stop.
```

## Run BC-1（BOM Compare 验收）

- 时间：`2025-12-19 12:39:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`bbda7eb6-754c-4255-8190-895ae53c719a`
  - Parent B：`0b882e4e-d876-437a-bd87-c2d0795b47a1`
  - Child X：`4398a927-9359-4b78-959f-473834170e60`
  - Child Y：`e0279135-b75d-4bb8-ac62-71b2d5c0d8dd`
  - Child Z：`217c502b-a6bc-49c9-a736-f0fd4ab92c5f`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
ALL CHECKS PASSED
```


## Run S4-4（ECO Advanced：Impact + BOM diff 联动）

- 时间：`2025-12-23 11:50:58 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_eco_advanced.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - ECO Stage：`937c7443-d7d0-45be-aa70-686f344d3632`
  - ECO1：`3e6395b8-23ea-42bf-a45a-ccb7f8af5428`
  - ECO2：`b350df1b-51cf-4dcd-ad88-1b50f1039b4a`
  - Product：`326e7a64-4655-4add-bc3c-2603047e20fb`
  - Assembly：`7020c406-1c62-46b9-b4e2-f1e701407322`
  - Source Version：`b577a733-0d92-4229-8985-0fd9d36cf06f`
  - Target Version：`498ab678-e1b4-474a-a497-07061db5ec67`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ECO impact analysis (include files + bom diff): OK
ECO Advanced Verification Complete
ALL CHECKS PASSED
```


## Run S4-5（ECO Advanced：Impact + Version Diff）

- 时间：`2025-12-23 11:58:21 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_eco_advanced.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - ECO Stage：`3c96202e-0bc3-449f-8a87-51482c3db1ad`
  - ECO1：`bd54086d-0d58-44e7-821f-997bc44ed0c7`
  - ECO2：`9369ef9e-db4e-4c41-a636-3f2c99f869db`
  - Product：`33767c45-1384-4e1c-893f-3292fda47ea5`
  - Assembly：`aed244e4-8bd2-4e38-bd8f-bbd7a46ad3ef`
  - Source Version：`7c12dca9-c80f-4c31-b372-a6b3203a9b37`
  - Target Version：`902b4b33-afc1-4adb-9328-4ac420694538`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ECO impact analysis (include files + bom diff + version diff): OK
ECO Advanced Verification Complete
ALL CHECKS PASSED
```


## Run S4-6（ECO Advanced：Impact Export CSV/XLSX/PDF）

- 时间：`2025-12-23 13:16:14 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_eco_advanced.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - ECO Stage：`9f13af28-8ca6-4242-a849-2568b800c497`
  - ECO1：`368943ca-7dd9-4e23-b88a-d8128851d46f`
  - ECO2：`578272e5-8423-4efa-a81c-30f569bd720b`
  - Product：`29744ca9-f5d8-4c5c-a12a-4e1fc547d34e`
  - Assembly：`068744d3-9fd2-4c34-a516-7808dab76b81`
  - Source Version：`a771b84f-cf9b-4ee1-a291-5c8639db1436`
  - Target Version：`eb301ef8-928c-4624-88ab-8d0c88c2122d`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ECO impact analysis (include files + bom diff + version diff): OK
Impact export files: OK
ECO Advanced Verification Complete
ALL CHECKS PASSED
```


## Run S2-1（Documents & Files 验收）

- 时间：`2025-12-22 23:44:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_documents.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`96e00dfd-bf8d-431b-9324-f39810c76fd4`
  - File：`f5fc9833-c276-4c35-8f10-72a44034be60`

执行命令：

```bash
bash scripts/verify_documents.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run ALL-20260120-2341（Full Regression + Ops S8 + Tenant Provisioning）

- 时间：`2026-01-20 23:43:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`（`RUN_OPS_S8=1`, `RUN_TENANT_PROVISIONING=1`）
- 日志：`/tmp/verify_all_20260120_234147.log`
- 结果：`PASS: 37  FAIL: 0  SKIP: 14`
- 环境：
  - `DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `YUANTUS_STORAGE_TYPE=s3`
  - `YUANTUS_S3_ENDPOINT_URL=http://localhost:59000`
  - `YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000`
  - `YUANTUS_S3_BUCKET_NAME=yuantus`
  - `YUANTUS_S3_ACCESS_KEY_ID=minioadmin`
  - `YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin`
  - `YUANTUS_CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200`

执行命令：

```bash
RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260120_234147.log
```

输出（摘要）：

```text
PASS: 37  FAIL: 0  SKIP: 14
ALL TESTS PASSED
```

## Run S7-20260120-2226（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-20 22:26:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=0 \
VERIFY_RETENTION_ENDPOINTS=0 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2258（Audit Retention + Endpoints）

- 时间：`2026-01-20 22:58:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 环境：
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `VERIFY_RETENTION=1`
  - `VERIFY_RETENTION_ENDPOINTS=1`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2259（Tenant Provisioning）

- 时间：`2026-01-20 22:59:57 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 环境：
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2317（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-20 23:17:38 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260120-2317（Tenant Provisioning）

- 时间：`2026-01-20 23:17:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 环境：
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260119-1355（Quota + Audit + Multi-Tenancy）

- 时间：`2026-01-19 13:55:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
DOCKER_HOST=unix:///Users/huazhou/Library/Containers/com.docker.docker/Data/docker.raw.sock \
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/Library/Containers/com.docker.docker/Data/docker.raw.sock \
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/Library/Containers/com.docker.docker/Data/docker.raw.sock \
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
verify_quotas.sh: ALL CHECKS PASSED
verify_audit_logs.sh: ALL CHECKS PASSED
verify_multitenancy.sh: ALL CHECKS PASSED
```

## Run S7-20260119-1204（Tenant Provisioning）

- 时间：`2026-01-19 12:04:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：启用平台管理员（platform tenant）后完成新租户/组织创建。
- 新租户：`tenant-provision-1768795448`
- 默认组织：`org-provision-1768795448`
- 额外组织：`org-extra-1768795448`

执行命令：

```bash
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run PROD-UI-20260114-1139（Product UI Aggregation）

- 时间：`2026-01-14 11:39:50 +0800`
- 脚本：`scripts/verify_product_ui.sh`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `SCHEMA_MODE=migrations`
- 关键对象：
  - Parent: `239af8cc-b108-4cd3-a0a6-5bff00356333`
  - Child: `32f5680d-81a6-4093-a4bb-8369ff4f3346`
  - BOM Line: `ca49b11d-6c92-4a2d-b8e0-2eb7adb116f9`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run WHERE-USED-UI-20260114-1139（Where-Used UI Payload）

- 时间：`2026-01-14 11:39:50 +0800`
- 脚本：`scripts/verify_where_used_ui.sh`
- 环境：同上
- 关键对象：
  - Grand: `a44cb4c5-09c7-4772-8769-7c18c818ee05`
  - Parent: `1065116b-fb98-4b75-91b5-04bbb1b1e495`
  - Child: `751a3a7e-1de3-457c-8176-bfa9623b6f1f`
  - parent_rel: `733e0a77-3930-4657-886f-2b7df6249564`
  - grand_rel: `cc629724-2843-419f-9b21-02ac88e0aa70`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run DOCS-ECO-UI-20260114-1139（Docs + ECO UI Summary）

- 时间：`2026-01-14 11:39:50 +0800`
- 脚本：`scripts/verify_docs_eco_ui.sh`
- 环境：同上
- 关键对象：
  - Part: `6c7f05f4-5347-40b1-b9cb-beb4155e5ec4`
  - Document: `746d4909-ea18-4b4a-830e-8d9c8d128602`
  - ECO: `51d7589f-ff62-4d45-bf6c-54df76e250a7`
  - ECO Stage: `90a1357a-f448-443a-b981-35dc33b31f39`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run PRODUCT-UI-LOCAL-20260114-1020（Product UI Aggregation, TestClient）

- 时间：`2026-01-14 10:20:38 +0800`
- 脚本：`scripts/verify_product_ui.sh`
- 方式：`LOCAL_TESTCLIENT=1`（本机禁用网络时的 in-process 验证）

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run WHERE-USED-UI-LOCAL-20260114-1020（Where-Used UI Payload, TestClient）

- 时间：`2026-01-14 10:20:38 +0800`
- 脚本：`scripts/verify_where_used_ui.sh`
- 方式：`LOCAL_TESTCLIENT=1`（本机禁用网络时的 in-process 验证）

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run DOCS-ECO-UI-LOCAL-20260114-1020（Docs + ECO UI Summary, TestClient）

- 时间：`2026-01-14 10:20:38 +0800`
- 脚本：`scripts/verify_docs_eco_ui.sh`
- 方式：`LOCAL_TESTCLIENT=1`（本机禁用网络时的 in-process 验证）

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```
```text
ALL CHECKS PASSED
```

## Run CAD-ML-PREVIEW-20260112-2208（CAD 2D 预览渲染）

- 时间：`2026-01-12 22:08:26 +0800`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 环境：`CAD_ML_BASE_URL=http://localhost:8000`，S3 storage（MinIO: `http://localhost:59000`）
- 样本：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE= \
YUANTUS_IDENTITY_DATABASE_URL= \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
CAD_ML_BASE_URL=http://localhost:8000 \
bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED (mesh stats optional: SKIP)
```

## Run CAD-ML-OCR-20260112-2208（CAD OCR 标题栏）

- 时间：`2026-01-12 22:08:26 +0800`
- 脚本：`scripts/verify_cad_ocr_titleblock.sh`
- 环境：`CAD_ML_BASE_URL=http://localhost:8000`，S3 storage（MinIO: `http://localhost:59000`）

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE= \
YUANTUS_IDENTITY_DATABASE_URL= \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
CAD_ML_BASE_URL=http://localhost:8000 \
bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run CADGF-PREVIEW-ONLINE-20260112-2208（CADGF 在线预览）

- 时间：`2026-01-12 22:08:26 +0800`
- 脚本：`scripts/verify_cad_preview_online.sh`
- 环境：`CADGF router http://localhost:9000`，S3 storage（MinIO: `http://localhost:59000`）
- 样本：`/Users/huazhou/Downloads/新建文件夹/converted/J0224022-06上罐体组件v1.dxf`
- 结果报告：`/tmp/cadgf_preview_online_report.md`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE= \
YUANTUS_IDENTITY_DATABASE_URL= \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
BASE_URL=http://127.0.0.1:7910 \
TENANT=tenant-1 \
ORG=org-1 \
SAMPLE_FILE="/Users/huazhou/Downloads/新建文件夹/converted/J0224022-06上罐体组件v1.dxf" \
SYNC_GEOMETRY=1 \
bash scripts/verify_cad_preview_online.sh
```

```text
login_ok=yes, upload_ok=yes, conversion_ok=yes, viewer_load=yes, manifest_rewrite=yes
```

## Run CAD-AUTO-PART-20260113-1004（Auto Create Part）

- 时间：`2026-01-13 10:04:26 +0800`
- 脚本：`scripts/verify_cad_auto_part.sh`
- 环境：`TENANCY=db-per-tenant-org`，S3 storage（MinIO: `http://localhost:59000`）

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_IDENTITY_DATABASE_URL= \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
bash scripts/verify_cad_auto_part.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACTOR-STUB-20260113-1004（Extractor Stub）

- 时间：`2026-01-13 10:04:26 +0800`
- 脚本：`scripts/verify_cad_extractor_stub.sh`
- 环境：`TENANCY=db-per-tenant-org`，S3 storage（MinIO: `http://localhost:59000`）

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_IDENTITY_DATABASE_URL= \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run CAD-2D-COVERAGE-20260113-1004（2D 连接器覆盖率离线统计）

- 时间：`2026-01-13 10:04:26 +0800`
- 脚本：`scripts/verify_cad_connector_coverage_2d.sh`
- 输入：`/Users/huazhou/Downloads/训练图纸/训练图纸`（DWG，最多 30 个）
- 输出：
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`

```bash
CAD_CONNECTOR_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸" \
CAD_CONNECTOR_COVERAGE_MAX_FILES=30 \
CAD_CONNECTOR_COVERAGE_EXTENSIONS=dwg \
bash scripts/verify_cad_connector_coverage_2d.sh
```

```text
CAD 2D Connector Coverage Complete
```

## Run REGRESSION-MT-REAL-20251229-0212（Full Regression + Real CAD Samples, db-per-tenant-org）

- 时间：`2025-12-29 02:12:31 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：`PASS=35, FAIL=0, SKIP=7`
- 备注：启用 `RUN_CAD_REAL_CONNECTORS_2D=1` 与 `RUN_CAD_REAL_SAMPLES=1`

执行命令：

```bash
RUN_CAD_REAL_CONNECTORS_2D=1 \
RUN_CAD_REAL_SAMPLES=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
CAD_SAMPLE_HAOCHEN_DWG='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_SAMPLE_ZHONGWANG_DWG='/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg' \
CAD_SAMPLE_DWG='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_SAMPLE_STEP='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp' \
CAD_SAMPLE_PRT='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 35  FAIL: 0  SKIP: 7
ALL TESTS PASSED
```

## Run REGRESSION-MT-20251229-0146（Full Regression, db-per-tenant-org）

- 时间：`2025-12-29 01:46:54 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：`PASS=33, FAIL=0, SKIP=9`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 33  FAIL: 0  SKIP: 9
ALL TESTS PASSED
```
## Run BOM-COMPARE-MT-20251229-0119（BOM Compare, db-per-tenant-org）

- 时间：`2025-12-29 01:19:16 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`2eb2aeaa-2873-4073-8590-88ec2c8e7fa1`
  - Parent B：`7dd00500-26fd-480b-b05a-fe61025ef277`
  - Child X：`65efe14e-bd1f-4d3e-9e90-ff36c7523fe4`
  - Child Y：`c6241bad-3fe5-45ab-859f-985870afbd0e`
  - Child Z：`0ccfdd76-52b0-42dc-b590-e2d7c672ab11`
  - Substitute：`04dff92d-a8ee-4cc9-a2a4-f2c50ad00294`

执行命令：

```bash
TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run BOM-SUBSTITUTES-MT-20251229-0119（BOM Substitutes, db-per-tenant-org）

- 时间：`2025-12-29 01:19:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_substitutes.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent：`c77a2a49-cc89-45b3-819c-c7d45f533d3a`
  - Child：`583ffca2-3408-4507-b863-26e2036f1c38`
  - BOM Line：`6e5930de-a6d3-4395-917a-b494d9a983ef`
  - Substitute 1：`f897ae50-1412-4ddd-ac78-bc14efc97c1b`
  - Substitute 2：`957bb8d3-7af4-4418-af01-ca58c2da93aa`

执行命令：

```bash
TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_substitutes.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```
## Run BOM-COMPARE-20251229-0053（BOM Compare）

- 时间：`2025-12-29 00:53:58 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`1b63c0db-0708-4d6b-b993-e4f971020e84`
  - Parent B：`b456ca7b-4920-43ae-b263-e587c934df16`
  - Child X：`58a6b875-a709-4d3e-906c-dc263925c66b`
  - Child Y：`3c0e0a84-7827-43be-a3cd-2b8667abff39`
  - Child Z：`314a74cb-8141-4191-9d79-99ba734ca051`
  - Substitute：`a4e8bd35-6c8a-4b3e-a50b-f88a286db424`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
TENANCY_MODE=single \
  bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run BOM-SUBSTITUTES-20251229-0054（BOM Substitutes）

- 时间：`2025-12-29 00:54:04 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_substitutes.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent：`33816bbd-c18b-4e9c-9e2b-667bcde89937`
  - Child：`5d68ff99-3149-404e-8468-94a849836254`
  - BOM Line：`e5038258-3cfd-448d-bdf9-848d62116281`
  - Substitute 1：`776f398e-0d74-44fb-b286-1304288901f5`
  - Substitute 2：`203aa27a-c7a0-44b0-be29-6bf4e0a6aec8`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
TENANCY_MODE=single \
  bash scripts/verify_substitutes.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```
## Run INTEGRATIONS-ATHENA-CLIENT-20251229-0012（Integrations Athena Client Credentials）

- 时间：`2025-12-29 00:12:38 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_integrations_athena.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：通过 client credentials 自动取 token（无 `X-Athena-Authorization` / service token）。

执行命令：

```bash
YUANTUS_ATHENA_BASE_URL='http://host.docker.internal:7700/api/v1' \
YUANTUS_ATHENA_TOKEN_URL='http://host.docker.internal:8180/realms/ecm/protocol/openid-connect/token' \
YUANTUS_ATHENA_CLIENT_ID='ecm-api' \
YUANTUS_ATHENA_CLIENT_SECRET='<redacted>' \
  docker compose up -d --no-deps --force-recreate api

YUANTUS_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

YUANTUS_TOKEN="$YUANTUS_TOKEN" VERIFY_CLIENT_CREDENTIALS=1 \
  bash scripts/verify_integrations_athena.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run INTEGRATIONS-ATHENA-SVC-20251228-2357（Integrations Athena Service Token）

- 时间：`2025-12-28 23:57:32 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_integrations_athena.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：通过 `YUANTUS_ATHENA_SERVICE_TOKEN` 验证服务级认证（token 为临时 Keycloak access_token）。  

执行命令：

```bash
ATHENA_TOKEN=$(curl -s -X POST http://localhost:8180/realms/ecm/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=unified-portal&username=admin&password=admin' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

YUANTUS_ATHENA_SERVICE_TOKEN="$ATHENA_TOKEN" docker compose up -d --no-deps --force-recreate api

YUANTUS_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

YUANTUS_TOKEN="$YUANTUS_TOKEN" YUANTUS_ATHENA_SERVICE_TOKEN="$ATHENA_TOKEN" \
  bash scripts/verify_integrations_athena.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run INTEGRATIONS-ATHENA-20251228-2347（Integrations Athena）

- 时间：`2025-12-28 23:47:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_integrations_athena.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：使用 `X-Athena-Authorization` + Yuantus JWT；服务级 token 未验证。

执行命令：

```bash
YUANTUS_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

ATHENA_TOKEN=$(curl -s -X POST http://localhost:8180/realms/ecm/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=unified-portal&username=admin&password=admin' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

YUANTUS_TOKEN="$YUANTUS_TOKEN" ATHENA_TOKEN="$ATHENA_TOKEN" \
  bash scripts/verify_integrations_athena.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-COVERAGE-2D-20251228-2255（CAD 2D Connector Coverage）

- 时间：`2025-12-28 22:55:49 +0800`
- 脚本：`scripts/verify_cad_connector_coverage_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 输出报告：
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`
- 说明：离线覆盖统计，目录 `/Users/huazhou/Downloads/训练图纸/训练图纸`，共 110 个 DWG。

执行命令：

```bash
CAD_CONNECTOR_COVERAGE_DIR='/Users/huazhou/Downloads/训练图纸/训练图纸' \
CAD_CONNECTOR_COVERAGE_EXTENSIONS='dwg' \
  bash scripts/verify_cad_connector_coverage_2d.sh
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-AUTO-PART-20251228-2251（CAD Auto Part）

- 时间：`2025-12-28 22:51:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_auto_part.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`437b78a7-a349-40da-bb2b-ea106e06a977`
  - File：`7868796e-51e4-4a6f-8eae-5283884b8dfb`
  - Attachment：`76370cb7-0f04-4ccc-ba75-b0c701a55e25`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_auto_part.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACTOR-SERVICE-20251228-2242（CAD Extractor Service）

- 时间：`2025-12-28 22:42:53 +0800`
- 基地址：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_service.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_cad_extractor_service.sh
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACTOR-EXTERNAL-20251228-2243（CAD Extractor External）

- 时间：`2025-12-28 22:43:07 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`a768f92c-112d-4a40-8469-b105d4d76a68`
  - Job：`81272fd8-29c4-40a1-835a-aa3ab2951347`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/tmp/yuantus_extractor_external.dwg' \
CAD_EXTRACTOR_EXPECT_KEY=file_ext \
CAD_EXTRACTOR_EXPECT_VALUE=dwg \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```


## Run ALL-35（一键回归脚本：verify_all.sh）

- 时间：`2025-12-22 23:52:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=21, FAIL=0, SKIP=2)`
- 关键 ID：
  - S2 Part：`482c2fc5-aa4a-40bf-9a0f-518282015488`
  - S2 File：`9d53dd6f-964e-4298-9f26-5648831c07c7`
  - MBOM Root：`263811ad-e9ad-4913-9594-6a0a073c1d3b`
  - HAOCHEN File：`7166981e-92df-4c58-9996-8c8757755bb0`
  - ZHONGWANG File：`433ccfc3-316d-42b9-a9bb-34dc7f0c849d`

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 21  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```


## Run ALL-36（一键回归脚本：verify_all.sh，审计+多租户）

- 时间：`2025-12-23 08:26:37 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=23, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- 审计：`enabled=true`
- 关键 ID：
  - S2 Part：`3b7dcf8d-5395-40bd-9361-c93865143ead`
  - S2 File：`547b3999-b3a4-44c3-9b96-d88e07a94aab`
  - MBOM Root：`e19812b9-f83d-41da-b6ba-cc6ddb66a39b`
  - HAOCHEN File：`b0dfd017-9cdb-461a-8d09-996239757425`
  - ZHONGWANG File：`d0a56173-6ece-4538-a35f-43a4738f98c0`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_AUDIT_ENABLED=true \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 23  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```
## Run S5-B-2（CAD 2D Connectors：新增浩辰/中望）

- 时间：`2025-12-22 23:48:57 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GSTARCAD File：`3cb1a56b-d19a-476f-9ec2-fcc2ed2b4f7a`
  - ZWCAD File：`631a0216-ed5f-4ffe-9626-685f9963272a`
  - HAOCHEN File：`afdd5dad-df2a-4bcb-a8a5-e7b8a61cc29d`
  - ZHONGWANG File：`0632085d-3698-413a-9a4d-d8815220a196`

执行命令：

```bash
bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```


## Run ALL-34（一键回归脚本：verify_all.sh）

- 时间：`2025-12-22 21:27:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=22, FAIL=0, SKIP=0)`
- 关键 ID（MBOM Convert）：
  - EBOM Root：`a2c6c8aa-0dfb-465c-8525-cdc13f82e41c`
  - EBOM Child：`d9ec5b13-f015-4ffb-8709-7b9d6d5090f7`
  - EBOM Substitute：`f971ab49-b26e-47b6-94f8-01c4aa1ddf01`
  - EBOM BOM Line：`3c2b5ac5-a6bd-4e89-89c1-ddc8a143144b`
  - MBOM Root：`d3c6bde0-d209-4761-a21a-43b13e33bd7c`
- 关键 ID（Item Equivalents）：
  - A：`8e5bc6a7-883d-4375-a4aa-b99d936101c0`
  - B：`3ce9a44b-e9ba-47c0-a9c4-6826bbf09a48`
  - C：`344cf5ab-5786-4792-8734-af732c1052be`

执行命令：

```bash
bash scripts/verify_all.sh
```

输出（摘要）：

```text
PASS: 22  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run EQ-1（Equivalents 验收）

- 时间：`2025-12-22 16:46:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_equivalents.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part A：`e8e0b3eb-1857-4681-a0ff-e94017cf160f`
  - Part B：`fdad1e03-6a62-400e-af84-26fcf41a5279`
  - Part C：`768be703-d9ab-4b83-b6f8-623166a9a3c5`
  - Equivalent A-B：`3c2864a9-80ae-4808-ba0d-7b1632b098bc`
  - Equivalent A-C：`3c71801f-c211-4232-8442-224d27bb15f2`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_equivalents.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```


## Run ALL-32（一键回归脚本：verify_all.sh，db-per-tenant-org，含 Item Equivalents）

- 时间：`2025-12-22 16:48:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=21, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 审计：`enabled=true`
- 关键 ID（Item Equivalents）：
  - Part A：`c5dde0c9-4f7a-4991-96ca-e82100f1f90c`
  - Part B：`5fa79101-cb0e-4ec9-a2d1-39f96f13c90f`
  - Part C：`0035c177-c1a5-4ee9-b2ff-b1df79727424`
  - Equivalent A-B：`daf7acca-b64a-4be7-af6d-ed8b641893ff`
  - Equivalent A-C：`1d28529b-a52e-4236-9159-bd392e845839`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 21  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run MBOM-1（MBOM 转换验收）

- 时间：`2025-12-22 17:19:58 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_mbom_convert.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - EBOM Root：`606f2a5d-4e13-4067-8987-57402a143a60`
  - EBOM Child：`76c07b63-207f-4d8f-84b9-55cfbecc27f7`
  - EBOM Substitute：`957d9327-8496-4530-b5e1-44f8e1873709`
  - EBOM BOM Line：`935f7462-8fec-4067-abf1-9108d6afa13b`
  - MBOM Root：`d5fa51c1-cb19-4b0f-8927-4daabe67cedd`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_mbom_convert.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
MBOM structure: OK
ALL CHECKS PASSED
```


## Run ALL-33（一键回归脚本：verify_all.sh，db-per-tenant-org，含 MBOM）

- 时间：`2025-12-22 17:19:58 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=22, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 审计：`enabled=true`
- 关键 ID（MBOM Convert）：
  - EBOM Root：`4d1caa24-5fd4-488b-be18-ffd9a68ca76d`
  - EBOM Child：`158fdf6b-b71e-4a2b-9574-9f318689e795`
  - EBOM Substitute：`1d851c63-2de1-4414-acb9-ee39eefc863c`
  - EBOM BOM Line：`8504500f-e77c-42ce-b143-8e9a61e636b6`
  - MBOM Root：`c09f9089-6e18-46ca-be08-68d6f1bc3a9c`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 22  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run ALL-31（一键回归脚本：verify_all.sh，db-per-tenant-org 全量）

- 时间：`2025-12-22 16:27:57 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=20, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 审计：`enabled=true`
- 关键 ID：未记录

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 20  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run S7-MT-1（Multi-Tenancy：db-per-tenant-org）

- 时间：`2025-12-22 16:16:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：无（脚本未输出）

执行命令：

```bash
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-MT-2（Multi-Tenancy：db-per-tenant-org）

- 时间：`2025-12-23 13:30:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：无（脚本未输出）

执行命令：

```bash
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```


## Run S7-Q-1（Quota enforce 验证）

- 时间：`2025-12-22 15:43:23 +0800`
- 基地址：`http://127.0.0.1:7911`
- 脚本：`scripts/verify_quotas.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
YUANTUS_DATABASE_URL='sqlite:///./tmp_quota_meta.db' \
YUANTUS_IDENTITY_DATABASE_URL='sqlite:///./tmp_quota_identity.db' \
YUANTUS_STORAGE_TYPE='local' \
YUANTUS_LOCAL_STORAGE_PATH='./data/storage_quota_test' \
  bash scripts/verify_quotas.sh http://127.0.0.1:7911 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```


## Run ALL-29（verify_all 回归）

- 时间：`2025-12-22 16:07:38 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 18 / FAIL 0 / SKIP 2`

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 18  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```


## Run ALL-30（Audit enabled 回归）

- 时间：`2025-12-22 16:10:38 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 19 / FAIL 0 / SKIP 1`
- 说明：`YUANTUS_AUDIT_ENABLED=true`

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 19  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```


## Run S7-Q-2（Quota enforce / Docker 7910）

- 时间：`2025-12-22 15:55:14 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_quotas.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-Q-3（Quota enforce / Docker 7910，db-per-tenant-org）

- 时间：`2025-12-23 13:29:44 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_quotas.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：`YUANTUS_QUOTA_MODE=enforce`

执行命令：

```bash
bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run BL-1（Baseline：BOM 快照/对比）

- 时间：`2025-12-22 12:02:28 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_baseline.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent：`716ebcea-6be3-4030-8cf5-331c6c2ca853`
  - Child B：`3d9c4d90-4a28-4545-99af-e8dc87f07b38`
  - Child C：`191c2c6c-31b5-41e8-bec9-ad540937a57e`
  - Baseline：`dd7ceb89-9db4-4c8f-8c61-6bbd8acd79da`

执行命令：

```bash
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_baseline.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run ALL-27（一键回归脚本：verify_all.sh，含 Baseline）

- 时间：`2025-12-22 12:02:28 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS: 17  FAIL: 0  SKIP: 2`
- 备注：`Audit Logs`、`S7 (Multi-Tenancy)` 在单租户模式下跳过

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 17  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```

## Run AUD-4（Audit Logs + Retention，单租户）

- 时间：`2025-12-22 12:18:27 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`
- 参数：
  - `AUDIT_RETENTION_DAYS=1`
  - `AUDIT_RETENTION_MAX_ROWS=5`
  - `AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`

执行命令：

```bash
AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Audit logs: OK
Audit retention: OK
ALL CHECKS PASSED
```

## Run S7-5（Multi-Tenancy：db-per-tenant-org，Docker overlay）

- 时间：`2025-12-22 12:18:27 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 模式：`db-per-tenant-org`

执行命令：

```bash
YUANTUS_SCHEMA_MODE=create_all \
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
Multi-Tenancy Verification Complete
ALL CHECKS PASSED
```

## Run ALL-28（一键回归脚本：verify_all.sh，db-per-tenant-org + Audit enabled）

- 时间：`2025-12-22 14:13:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS: 19  FAIL: 0  SKIP: 0`
- 模式：`db-per-tenant-org`
- 审计保留：`max_rows=5, days=1, prune_interval=1`
- 关键 ID（S5-C）：
  - Item：`21f94a57-006e-4b07-8655-49950f1dea24`
  - File：`456e843f-abc0-491a-a074-f144c681b761`
  - Job：`4f22084c-3f00-4914-9598-e6951f567543`

执行命令：

```bash
AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 19  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run BK-1（Backup/Restore 验证）

- 时间：`2025-12-22 14:48:33 +0800`
- 脚本：`scripts/verify_backup_restore.sh`
- 结果：`ALL CHECKS PASSED`
- 备份目录：`/tmp/yuantus_backup_verify_1766386083`
- 还原 DB 后缀：`_restore_1766386083`
- 还原 Bucket：`yuantus-restore-test-1766386083`

执行命令：

```bash
bash scripts/verify_backup_restore.sh
```

输出（摘要）：

```text
Backup/Restore Verification Complete
ALL CHECKS PASSED
```

## Run BK-2（Cleanup Restore 验证）

- 时间：`2025-12-22 15:00:32 +0800`
- 脚本：`scripts/verify_cleanup_restore.sh`
- 结果：`ALL CHECKS PASSED`
- 清理目标：
  - DB：`yuantus_cleanup_test_1766386824`
  - Bucket：`yuantus-cleanup-test-1766386824`

执行命令：

```bash
bash scripts/verify_cleanup_restore.sh
```

输出（摘要）：

```text
Cleanup Verification Complete
ALL CHECKS PASSED
```

## Run BK-6（Cleanup Restore 验证）

- 时间：`2025-12-23 13:40:37 +0800`
- 脚本：`scripts/verify_cleanup_restore.sh`
- 结果：`ALL CHECKS PASSED`
- 清理目标：
  - DB：`yuantus_cleanup_test_1766468424`
  - Bucket：`yuantus-cleanup-test-1766468424`
- 说明：`PROJECT=yuantusplm`

执行命令：

```bash
bash scripts/verify_cleanup_restore.sh
```

输出（摘要）：

```text
Cleanup Verification Complete
ALL CHECKS PASSED
```

## Run BK-3（Backup Rotation 验证）

- 时间：`2025-12-22 15:04:34 +0800`
- 脚本：`scripts/verify_backup_rotation.sh`
- 结果：`ALL CHECKS PASSED`
- 参数：`KEEP=2`（默认）

执行命令：

```bash
bash scripts/verify_backup_rotation.sh
```

输出（摘要）：

```text
Rotation complete.
ALL CHECKS PASSED
```

## Run BK-4（Backup/Restore 验证）

- 时间：`2025-12-23 13:26:34 +0800`
- 脚本：`scripts/verify_backup_restore.sh`
- 结果：`ALL CHECKS PASSED`
- 备份目录：`/tmp/yuantus_backup_verify_1766467544`
- 还原 DB 后缀：`_restore_1766467544`
- 还原 Bucket：`yuantus-restore-test-1766467544`
- 说明：`PROJECT=yuantusplm`

执行命令：

```bash
PROJECT=yuantusplm BACKUP_DIR=/tmp/yuantus_backup_verify_1766467544 \
  bash scripts/verify_backup_restore.sh
```

输出（摘要）：

```text
Backup/Restore Verification Complete
ALL CHECKS PASSED
```

## Run BK-5（Backup Rotation 验证）

- 时间：`2025-12-23 13:27:20 +0800`
- 脚本：`scripts/verify_backup_rotation.sh`
- 结果：`ALL CHECKS PASSED`
- 参数：`KEEP=2`（默认）

执行命令：

```bash
bash scripts/verify_backup_rotation.sh
```

输出（摘要）：

```text
Rotation complete.
ALL CHECKS PASSED
```


## Run ALL-26（一键回归脚本：verify_all.sh，db-per-tenant-org）

- 时间：`2025-12-22 09:43:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=18, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 关键 ID（S5-C）：
  - Item：`fd2f5558-d210-4233-8ebf-a3965f81bcea`
  - File：`ac0dedeb-278a-46ea-88c4-cf9af325e490`
  - Job：`a50208fe-d932-4afe-8d9f-e2844ce7ced2`

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 18  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run BC-2（BOM Compare 字段级差异 + 严重度验收）

- 时间：`2025-12-19 22:40:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`af9f8507-26ac-47c4-a352-ba4a105baf2a`
  - Parent B：`d855fdff-2001-4691-9618-7be638b10a05`
  - Child X：`a15dbbcf-0c49-419b-a10c-8d9528b98125`
  - Child Y：`139480e4-251c-411c-acd5-874837c6108a`
  - Child Z：`edf3af9f-8da6-4b44-bdac-739b531bbf1f`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK (changes list + severity=major validated)
ALL CHECKS PASSED
```

## Run ALL-3（一键回归脚本：verify_all.sh，BOM Compare 通过）

- 时间：`2025-12-19 12:40:31 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=8, FAIL=0, SKIP=0)`
- 关键 ID（节选）：
  - Run H Part：`4317a9e4-f85c-4e4b-a66a-e42246f8ee29`
  - Run H RPC Part：`c573f16f-8ca0-40c9-a34d-dc7f7ad4451a`
  - Run H File：`fd00ad42-1bf6-44d8-afac-9ab2a11d29b7`
  - Run H ECO：`b459563f-ea74-441f-bd71-4a4d52a59e1a`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Where-Used Component：`87b7f1f4-456c-4d48-9ed6-3268ea44559c`
  - BOM Compare Parent A：`fbc75d37-c158-45ef-a2d9-a03d0e9391db`
  - BOM Compare Child Z：`6e662fa4-2598-4aa2-8b51-a344e639aa43`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S5-A (CAD Pipeline S3)    PASS
Where-Used API            PASS
BOM Compare               PASS

PASS: 8  FAIL: 0  SKIP: 0

ALL TESTS PASSED
```

## Release v0.1.1（Docs Update）

- 时间：`2025-12-19 14:40:21 +0800`
- Release：`https://github.com/zensgit/yuantus-plm/releases/tag/v0.1.1`
- 包：`dist/yuantusplm-20251219-144021.tar.gz`
- 说明：补充 README 徽章与 CONTRIBUTING/SECURITY 文档，Release 与当前 main 对齐。

## Run S1（Meta + RBAC 强化验收）

- 时间：`2025-12-19 08:56:02 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_permissions.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - PermissionSet：`ReadOnly-1766105762`
  - Part：`68b72d21-521a-4726-bdf8-be214996a074`
  - Child Part：`78cd4129-4bc4-46cf-8db4-ce835cb6dfba`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
bash scripts/verify_permissions.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Created PermissionSet: ReadOnly-1766105762
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=68b72d21-521a-4726-bdf8-be214996a074)
Admin created child Part: OK (child_id=78cd4129-4bc4-46cf-8db4-ce835cb6dfba)
==> Login as viewer
Viewer login: OK
==> Viewer READ operations (should succeed)
Viewer AML get Part: OK (200)
Viewer search: OK (200)
Viewer BOM effective: OK (200)
==> Viewer WRITE operations (should fail with 403)
Viewer AML add Part: BLOCKED (403) - EXPECTED
Viewer BOM add child: BLOCKED (403) - EXPECTED
Viewer AML update Part: BLOCKED (403) - EXPECTED
==> Admin WRITE operations (should succeed)
Admin BOM add child: OK
Admin AML update Part: OK
==> Viewer can read updated BOM tree
Viewer BOM tree with children: OK (200)

ALL CHECKS PASSED
```

## Run S3.1（多级 BOM + 循环检测验收）

- 时间：`2025-12-19 08:57:31 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_tree.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part A：`b7b667d1-8925-45be-a012-003a514087cd`
  - Part B：`af5c794e-613e-4598-82b3-d06011a76183`
  - Part C：`1e4caced-57b2-423b-bf80-e1ac9ff4bd7f`
  - Part D：`b18992f3-b1ae-419c-bca2-e29f1306614a`
  - Rel A→B：`3f2c208b-2f4f-4121-9356-3e20ea00cc45`
  - Rel B→C：`8992cbec-fc1f-4f5e-89d3-f7763db4ec55`
  - Rel B→D：`8461cbfe-b479-46a4-acfe-bdfee08c92d0`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create test parts for BOM tree
Created Part A: b7b667d1-8925-45be-a012-003a514087cd
Created Part B: af5c794e-613e-4598-82b3-d06011a76183
Created Part C: 1e4caced-57b2-423b-bf80-e1ac9ff4bd7f
Created Part D: b18992f3-b1ae-419c-bca2-e29f1306614a
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: 3f2c208b-2f4f-4121-9356-3e20ea00cc45
Adding C as child of B...
B -> C relationship created: 8992cbec-fc1f-4f5e-89d3-f7763db4ec55
Adding D as child of B...
B -> D relationship created: 8461cbfe-b479-46a4-acfe-bdfee08c92d0
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: ['1e4caced-57b2-423b-bf80-e1ac9ff4bd7f', 'b7b667d1-8925-45be-a012-003a514087cd', 'af5c794e-613e-4598-82b3-d06011a76183', '1e4caced-57b2-423b-bf80-e1ac9ff4bd7f']: OK
==> Test self-reference cycle (A -> A should be 409)
Self-reference cycle: A -> A returned 409: OK
==> Test duplicate add (A -> B again should fail)
Duplicate add: A -> B again returned 400: OK
==> Test remove child (B -> D)
Remove child: B -> D deleted: OK
After delete: Level 2 has 1 child (C only): OK
==> Test remove non-existent relationship
Remove non-existent: A -> D (never existed) returned 404: OK

ALL CHECKS PASSED
```

## Run S3.2（BOM Effectivity 生效性验收）

- 时间：`2025-12-19 09:17:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_effectivity.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part A：`38a687e0-6645-4cfd-aee7-d75c1186f8af`
  - Part B：`afe0ffa7-f8cd-476b-be36-09d1e3023594`
  - Part C：`ca639d6c-ddd3-4ae7-85d2-55d293565af5`
  - Part D：`fac6cb0c-fbd3-411d-a9d7-c4839570ea6b`
  - Rel A→B：`f2bd3e89-1c0f-47d5-ad5a-536d4fc43f30`
  - Effectivity（A→B）：`f2ff2459-3900-4927-b4a6-0c5c60b7f7a2`
  - Rel A→C：`c49a3395-22b2-43e0-84b1-2160220edaf9`
  - Rel A→D：`a179f16b-56ba-4fa8-8df2-9bc0c23d1a07`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
bash scripts/verify_bom_effectivity.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
Date context: TODAY=2025-12-19T01:17:39Z, NEXT_WEEK=2025-12-26T01:17:39Z, LAST_WEEK=2025-12-12T01:17:39Z
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): 38a687e0-6645-4cfd-aee7-d75c1186f8af
Created Part B (future child): afe0ffa7-f8cd-476b-be36-09d1e3023594
Created Part C (current child): ca639d6c-ddd3-4ae7-85d2-55d293565af5
Created Part D (expired child): fac6cb0c-fbd3-411d-a9d7-c4839570ea6b
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: f2bd3e89-1c0f-47d5-ad5a-536d4fc43f30, effectivity_id: f2ff2459-3900-4927-b4a6-0c5c60b7f7a2
Adding C to A (effective from last week, always visible now)...
A -> C relationship: c49a3395-22b2-43e0-84b1-2160220edaf9
Adding D to A (expired - ended last week)...
A -> D relationship: a179f16b-56ba-4fa8-8df2-9bc0c23d1a07
BOM with effectivity created: OK
==> Query effective BOM at TODAY (should only see C)
Effective BOM at TODAY: 1 child (C only): OK
==> Query effective BOM at NEXT_WEEK (should see B and C)
Effective BOM at NEXT_WEEK: 2 children (B and C): OK
==> Query effective BOM at LAST_WEEK (should see C and D)
Effective BOM at LAST_WEEK: 2 children (C and D): OK
==> RBAC: Viewer cannot add BOM children (should be 403)
Viewer login: OK
Viewer add BOM child: BLOCKED (403) - EXPECTED
==> RBAC: Viewer can read effective BOM (should be 200)
Viewer read effective BOM: OK (200)
==> Delete BOM line (A -> B) and verify Effectivity CASCADE
Delete A -> B relationship: OK
After delete: NEXT_WEEK shows 1 child (C only): OK

ALL CHECKS PASSED
```

## Run S3.3（版本语义与规则固化验收）

- 时间：`2025-12-19 09:34:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_versions.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`2d52b642-5162-47e4-a260-5005ae68d541`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
bash scripts/verify_versions.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create versionable Part
Created Part: 2d52b642-5162-47e4-a260-5005ae68d541
==> Initialize version (expecting 1.A)
Initial version: 1.A (generation=1, revision=A): OK
==> Revise version (1.A -> 1.B)
Revised version: 1.B: OK
==> Revise version again (1.B -> 1.C)
Revised version: 1.C: OK
==> Get version tree
Version tree has 3 versions (1.A, 1.B, 1.C): OK
Version tree labels: 1.A,1.B,1.C: OK
==> Get version history
Version history has 3 entries: OK
==> Test revision calculation
Letter scheme: A -> B: OK
Letter scheme: Z -> AA: OK
Number scheme: 1 -> 2: OK
==> Test revision comparison
Revision compare: A < C: OK
==> Test iteration within version
Created iteration: 1.C.1: OK
Created iteration: 1.C.2: OK
Latest iteration is 1.C.2: OK
==> Test version comparison
Version comparison (1.A vs 1.B): OK
==> Create revision scheme
Created revision scheme (number, starts at 1): OK
Revision schemes list: 1 scheme(s): OK
==> Test checkout/checkin flow
Checkout: locked by user 1: OK
Checkin: unlocked: OK

ALL CHECKS PASSED
```

## Run S5-A（S3 CAD Pipeline：preview/geometry 302 + presigned URL 可回读）

- 时间：`2025-12-19 10:15:56 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_pipeline_s3.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Preview Job：`36ef466d-36fb-4871-9379-91eb2cb479da`
  - Geometry Job：`9766557b-9f4f-40c8-a8bb-4e519334d216`

执行命令：

```bash
# 确保 docker API/worker 已包含最新代码
docker compose up -d --build api worker

# 本地 CLI/worker 连接 docker Postgres + MinIO
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'

bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
==============================================
S3 CAD Pipeline Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity (admin user)
OK: Identity seeded

==> Seed meta schema
OK: Meta schema seeded

==> Login as admin
OK: Admin login

==> Create test STL file
OK: Created test file: /tmp/yuantus_cad_s3_test.stl

==> Upload STL via /cad/import
OK: File uploaded: a5033222-ec3c-4345-b54a-c5fa0de20cc3
Preview job ID: 36ef466d-36fb-4871-9379-91eb2cb479da
Geometry job ID: 9766557b-9f4f-40c8-a8bb-4e519334d216

==> Run worker to process jobs
OK: Worker executed

==> Check job statuses
Preview job status: completed
Geometry job status: completed

==> Check file metadata
Preview URL: /api/v1/file/a5033222-ec3c-4345-b54a-c5fa0de20cc3/preview
Geometry URL: /api/v1/file/a5033222-ec3c-4345-b54a-c5fa0de20cc3/geometry
Conversion status: completed
OK: Preview path set
OK: Geometry path set

==> Test preview endpoint
OK: Preview endpoint works (HTTP 302)

==> Test geometry endpoint
OK: Geometry endpoint works (HTTP 302)

==> Check storage type
OK: S3 storage detected (302 redirect)
Testing S3 presigned URL follow (no API auth headers)...
OK: S3 presigned URL accessible (followed redirect)

==> Cleanup
OK: Cleaned up test file

==============================================
CAD Pipeline S3 Verification Complete
==============================================

Summary:
  - File upload: OK
  - Job processing: completed / completed
  - Preview endpoint: 302
  - Geometry endpoint: 302

ALL CHECKS PASSED
```

## Run S5-B（CAD 2D Connectors：GStarCAD/ZWCAD）

- 时间：`2025-12-19 16:04:47 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`351314c3-38a0-49a0-888f-24499ba82501`
  - ZWCAD File：`cf13598c-7b25-45c9-a7aa-542c21538288`

执行命令：

```bash
# 重建 API/worker 以包含最新代码
docker compose --project-name yuantusplm up -d --build api worker

DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
==============================================
CAD 2D Connectors Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta
==> Login as admin
OK: Admin login
==> Create dummy DWG/DXF files
OK: Created files: /tmp/yuantus_gstarcad_1766131469.dwg, /tmp/yuantus_zwcad_1766131469.dxf
==> Upload gstarcad_1766131469.dwg (GSTARCAD)
OK: Uploaded file: 351314c3-38a0-49a0-888f-24499ba82501
Metadata OK
OK: Metadata verified (GSTARCAD)
==> Upload zwcad_1766131469.dxf (ZWCAD)
OK: Uploaded file: cf13598c-7b25-45c9-a7aa-542c21538288
Metadata OK
OK: Metadata verified (ZWCAD)
==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 2D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
```

## Run S5-B-2（CAD 2D Connectors：Registry 集成验证）

- 时间：`2025-12-19 18:02:03 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`4b29c5ec-bc2d-4abc-a077-f79590d69d79`
  - ZWCAD File：`a17eeada-af51-4744-bbd5-c910b624a646`

执行命令：

```bash
docker compose --project-name yuantusplm up -d --build api worker

DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Upload gstarcad... (GSTARCAD) -> OK
Upload zwcad... (ZWCAD) -> OK
ALL CHECKS PASSED
```

## Run S5-C（CAD Attribute Sync：x-cad-synced mapping）

- 时间：`2025-12-19 22:00:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`958ada4d-c0e9-448c-bb4b-113bec986e91`
  - Job：`9c3e6d73-c504-4991-b94f-f772b55a93a9`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Created Part: 958ada4d-c0e9-448c-bb4b-113bec986e91
Created job: 9c3e6d73-c504-4991-b94f-f772b55a93a9
Job completed
CAD sync mapping verified
ALL CHECKS PASSED
```

## Run ALL-8（一键回归脚本：verify_all.sh，含 S5-B）

- 时间：`2025-12-19 16:16:29 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=12, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`5b0c0b18-8996-4094-afcc-eef1156261d9`
  - Run H RPC Part：`b4c43470-71d5-43e8-b7f5-1ec2d7c46eb8`
  - Run H File：`7efa0a49-f3dd-43dd-a9eb-441b10827fd7`
  - Run H ECO：`50126418-0f9f-4b2a-bf78-94622a0a90fe`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`90473a1f-e8c1-421a-8a45-19a6d97b14c9`
  - S5-B ZWCAD File：`1f54bb32-5ae5-4310-b2a1-04ee2ac6d5e4`

执行命令：

```bash
YUANTUS_SCHEMA_MODE=migrations \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 12  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-9（一键回归脚本：verify_all.sh，含 S5-C）

- 时间：`2025-12-19 22:23:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=13, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`5e5b0002-f910-4157-9cd3-ade659fd3260`
  - Run H RPC Part：`f174e942-012d-46d6-b498-305900768186`
  - Run H File：`dd80e8c3-1a54-4e1b-acb4-417b6bde1bd9`
  - Run H ECO：`c35a4224-2dd5-4454-9a32-b4bf96ff6847`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`7d75e309-0bc4-49d3-903e-a0b4fc621dd5`
  - S5-B ZWCAD File：`597c6a6f-f65d-4916-8d06-32af4f300c2b`
  - S5-C Item：`d1a8dcbd-351f-4917-b527-e6674c1134a5`
  - S5-C Job：`3423ba0f-0fa8-4124-97a1-18e664ddda64`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 13  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-10（一键回归脚本：verify_all.sh，含 BOM Compare 字段级差异）

- 时间：`2025-12-19 23:02:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=13, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`053aa3d3-014d-4af0-bcdd-be16bf34220f`
  - Run H RPC Part：`52cb6ebb-b082-4261-8fdd-51e954dfa49f`
  - Run H File：`d459c41a-8c8f-4e64-bc40-7f0fdb123e19`
  - Run H ECO：`b1712287-e6be-4233-890d-88ba35a226cd`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`bc034980-fb47-498d-bb37-1a3d378902b4`
  - S5-B ZWCAD File：`2295004e-3838-402b-a3f5-500830a7597d`
  - S5-C Item：`8d19710e-6d66-4255-9b83-45b00b9f430d`
  - S5-C Job：`94e8f8b0-4602-4f79-94c8-a6db38d79ab7`
  - BOM Compare Parent A：`f2344544-03e4-4437-a4a1-1b8c15186e3f`
  - BOM Compare Child Z：`337cdc96-88b7-456f-a3ee-85e96cba30e4`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 13  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-11（一键回归脚本：verify_all.sh，含 ECO Impact 分级）

- 时间：`2025-12-19 23:19:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=13, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`3794c9b1-93d1-4a52-afda-7c972355a4ff`
  - Run H RPC Part：`f0b60371-2880-4f32-998d-07573d10af25`
  - Run H File：`42f341c1-4239-4861-83b7-a2b318e3fb85`
  - Run H ECO：`f89df011-8fe8-46c6-aa5e-1af82613929d`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`35962076-f593-4ac0-bede-de5acb5f35df`
  - S5-B ZWCAD File：`2a1cd37c-95dd-4224-b5b2-0fb43f67f827`
  - S5-C Item：`dffb9fb2-6d9f-49f3-a695-e8118a3ced4a`
  - S5-C Job：`112f73d5-f3b1-4510-b5c9-9dd645447643`
  - BOM Compare Parent A：`84fc9046-222e-477b-9ee6-2853b262f010`
  - BOM Compare Child Z：`9a41c8ed-62e7-43ee-babc-3648e774be14`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 13  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-12（一键回归脚本：verify_all.sh，DB_URL 对齐）

- 时间：`2025-12-19 23:54:21 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=13, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`a95265ea-9297-440f-9fc3-09a40838de98`
  - Run H RPC Part：`9d865c92-1669-4e23-9c31-82ed6852e138`
  - Run H File：`9891e7dc-adc2-4f69-bd16-8aa81f9d6bea`
  - Run H ECO：`ee2e5d45-624b-47ad-a837-ba4eeb94cb13`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`6d35f02a-ae82-4c26-ad1e-bc567158a5a0`
  - S5-B ZWCAD File：`0a904675-2f18-430f-95e0-7d71540199a1`
  - S5-C Item：`5f816d7d-d534-4604-9820-154ed0018663`
  - S5-C Job：`0a88da6d-8189-418a-973c-252a4557168f`
  - BOM Compare Parent A：`3e39f9ab-5e95-4957-b414-a063e67c0f42`
  - BOM Compare Child Z：`bd21ac7f-02e4-497f-9fc1-b51b8556e095`
  - BOM Substitutes Parent：`ab22acde-4786-4e38-b394-967ddb53e026`
  - Version-File Binding Part：`23e62da1-000e-4205-8e46-f6e7b9c3efb0`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 13  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-13（一键回归脚本：verify_all.sh，复现记录）

- 时间：`2025-12-19 23:58:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=13, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`153038d1-84bb-42e2-b313-8f0ab0ac187c`
  - Run H RPC Part：`baef079b-090f-41c3-a268-c4a296a915ae`
  - Run H File：`b9521cb8-7fb0-4c08-a19d-2f098f1f069f`
  - Run H ECO：`943a7ee6-ce7f-4d32-ad3a-5f9cf82ca3b5`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`c977e90e-aef9-40af-aa69-502dff3d0188`
  - S5-B ZWCAD File：`858a7428-5720-4791-8b57-79d86fa30eaa`
  - S5-C Item：`1caf8378-3977-4f74-8233-07ff67a1d1df`
  - S5-C Job：`d8d2b0a1-9be7-4d00-87fc-a177bad4c551`
  - BOM Compare Parent A：`2e43f934-c2a0-4971-84b9-cba51696721d`
  - BOM Compare Child Z：`69a06b39-a434-49d3-952b-d8b8aee1621b`
  - BOM Substitutes Parent：`0f030a83-a068-48b2-8539-9edde6d25c0b`
  - Version-File Binding Part：`3fc6e43e-9f69-4bd5-9600-f1eab93b9db8`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 13  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-14（一键回归脚本：verify_all.sh，含 Search Index）

- 时间：`2025-12-20 08:57:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=14, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`03445de3-0e85-4d0d-a4c7-cb5b036846e7`
  - Run H RPC Part：`204b72ca-b4b3-4335-88fe-2f2257af717f`
  - Run H File：`e624a7e6-22e0-40c6-916b-49f43b8bc8e0`
  - Run H ECO：`2f3624fb-2836-470b-bd48-bb0266a72212`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`80a4a6f7-7d97-427d-bec3-35d4f98478d7`
  - S5-B ZWCAD File：`7bd426bb-a351-457d-87df-d11a2e85f2e0`
  - S5-C Item：`2ff09810-3d9a-4fea-aec5-e1c474861204`
  - S5-C Job：`f95add7e-eba8-443e-b1bb-667ea27fc2b5`
  - Search Index Part：`5dce849a-5114-40ed-a513-fe3fffbbe625`
  - BOM Compare Parent A：`e82587b4-2f9d-495f-b3ef-3405cf658cb5`
  - BOM Compare Child Z：`e1dadcc2-ff24-48ce-b000-e23e1516b678`
  - BOM Substitutes Parent：`e3bcf763-515d-40c5-a771-cd5d65d71843`
  - Version-File Binding Part：`a6f83a32-2e88-4b22-8dc7-508e28271983`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
Search Index              PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 14  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run ALL-15（一键回归脚本：verify_all.sh，含 Reports Summary）

- 时间：`2025-12-20 11:04:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=15, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`3b227e65-7a08-4916-8665-d4e7df0cac58`
  - Run H RPC Part：`2ea8abe3-844b-4c56-8d75-9b020085c764`
  - Run H File：`23c41694-fc75-4813-aed7-0ebc86cf4119`
  - Run H ECO：`0f3d0e47-35e8-4cf6-8c22-313a584ab584`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`0e008a10-6060-4e78-a0f4-c7febdce0d64`
  - S5-B ZWCAD File：`c956c2fa-6368-4e23-99f9-ce80693dcadd`
  - S5-C Item：`a26424f8-6251-4727-b0d8-7a3430fb527f`
  - S5-C Job：`e3610486-ba00-4cda-95b0-2f27729618f9`
  - Search Index Part：`6362bcfe-2ba1-4f0b-9764-fbac6eba203a`
  - Reports Summary Part：`eb585662-22fb-425f-b98d-545a97d06ccd`
  - Reports Summary File：`c411efb7-8808-4cad-91f4-a8d51bcc8049`
  - Reports Summary ECO：`9c1b327c-7baa-48a2-a0f7-9246f4b8216d`
  - Reports Summary Job：`e34f2a6e-05bb-4445-958a-60b061176d12`
  - BOM Compare Parent A：`b241714c-c422-4670-a8e1-f80d492c8a72`
  - BOM Compare Child Z：`a3f9bc8f-d715-43af-8dd9-bdd3a153a687`
  - BOM Substitutes Parent：`22d01592-1b74-4276-bfdc-c5250ae96238`
  - Version-File Binding Part：`d4aa3ef4-b3bd-4a9b-95c4-b212e67bf3bf`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
Search Index              PASS
Reports Summary           PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 15  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run MT-1（S7 多租户隔离：db-per-tenant-org）

- 时间：`2025-12-20 11:16:44 +0800`
- 基地址：`http://127.0.0.1:7920`
- 模式：`db-per-tenant-org`
- 数据库：`sqlite:///yuantus_mt_run4.db`
- Identity DB：`sqlite:///yuantus_identity_mt_run4.db`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：脚本仅校验隔离计数，未输出具体 item_id

执行命令：

```bash
MODE=db-per-tenant-org \
DB_URL=sqlite:///yuantus_mt_run4.db \
IDENTITY_DB_URL=sqlite:///yuantus_identity_mt_run4.db \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7920 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
OK: Seeded tenant/org schemas
OK: Login succeeded
OK: Org + tenant isolation (A1)
OK: Org isolation (A2)
OK: Tenant isolation (B1)

ALL CHECKS PASSED
```

## Run MT-2（S7 多租户隔离：Postgres db-per-tenant-org）

- 时间：`2025-12-20 11:43:25 +0800`
- 基地址：`http://127.0.0.1:7921`
- 模式：`db-per-tenant-org`
- 数据库模板：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- Identity DB：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：创建了租户/组织数据库（未删除）

执行命令：

```bash
MODE=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7921 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
OK: Seeded tenant/org schemas
OK: Login succeeded
OK: Org + tenant isolation (A1)
OK: Org isolation (A2)
OK: Tenant isolation (B1)

ALL CHECKS PASSED
```

## Run MT-3（S7 多租户隔离：Docker Compose 覆盖模式）

- 时间：`2025-12-20 12:27:17 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 入口：`docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：验证后已切回单租户（`docker compose -f docker-compose.yml up -d --build`）

执行命令：

```bash
docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build

MODE=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2

docker compose -f docker-compose.yml up -d --build
```

输出（摘要）：

```text
OK: Seeded tenant/org schemas
OK: Login succeeded
OK: Org + tenant isolation (A1)
OK: Org isolation (A2)
OK: Tenant isolation (B1)

ALL CHECKS PASSED
```

## Run MT-4（S7 多租户隔离：Docker Compose 覆盖模式 + Wheelhouse）

- 时间：`2025-12-21 11:48:42 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 入口：`docker compose -p yuantusplm -f docker-compose.yml -f docker-compose.mt.yml up -d --build`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 备注：验证后已切回单租户（`docker compose -p yuantusplm -f docker-compose.yml up -d --build`）

执行命令：

```bash
docker compose -p yuantusplm -f docker-compose.yml -f docker-compose.mt.yml up -d --build

MODE=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2

docker compose -p yuantusplm -f docker-compose.yml up -d --build
```

输出（摘要）：

```text
OK: Seeded tenant/org schemas
OK: Login succeeded
OK: Org + tenant isolation (A1)
OK: Org isolation (A2)
OK: Tenant isolation (B1)

ALL CHECKS PASSED
```

---

## Run ALL-17（一键回归脚本：verify_all.sh，Docker 镜像 + Wheelhouse）

- 时间：`2025-12-21 11:45:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=16, FAIL=0, SKIP=1)`
- 备注：`audit_enabled=true`，镜像构建使用 `requirements.lock` + `vendor/wheels`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
Search Index              PASS
Reports Summary           PASS
Audit Logs                PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 16  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```

---

## Run ALL-16（一键回归脚本：verify_all.sh，切回单租户后）

- 时间：`2025-12-20 13:04:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=15, FAIL=0, SKIP=1)`
- 关键 ID（节选）：
  - Run H Part：`4db32437-632f-448d-b7e5-9feac2d4b4cb`
  - Run H RPC Part：`c02dafe6-41bc-43e4-8cbc-d7eb7e42710a`
  - Run H File：`f065623e-c0e8-419a-aa97-b9a331f8ade1`
  - Run H ECO：`7b79aa76-b341-4e28-8185-c3b3f115f8ee`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - S5-B GStarCAD File：`36bb215d-e9ef-411e-8124-1aa61ef4b51d`
  - S5-B ZWCAD File：`2516c32b-f593-410f-8a35-0995dc8a6851`
  - S5-C Item：`c81550be-6af1-41e3-88a2-c5c495c1e651`
  - S5-C Job：`bde68f6c-fca7-4101-a1ad-0174b6137763`
  - Search Index Part：`83b8201f-ca6b-427d-872e-168f8849cf49`
  - Reports Summary Part：`12afd4f5-59d7-47c5-876d-cde018319393`
  - Reports Summary File：`cd1890c8-b928-49e8-babb-6d8771159096`
  - Reports Summary ECO：`f257b2a4-18d6-4172-92ca-65d040d40bd4`
  - Reports Summary Job：`ca488c57-4905-4bd0-a896-ee56ac3b6528`
  - BOM Compare Parent A：`f4e3f2f8-ed79-454f-bcd8-9f9f3363839f`
  - BOM Compare Child Z：`69e18905-006b-4eaf-9e08-f10b451250b7`
  - BOM Substitutes Parent：`ff834ba0-34e9-46b5-a18a-2767c5085e9e`
  - Version-File Binding Part：`adfe03c4-9463-48b8-ae96-ed7b02497e2d`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S4 (ECO Advanced)         PASS
S5-A (CAD Pipeline S3)    PASS
S5-B (CAD 2D Connectors)  PASS
S5-C (CAD Attribute Sync) PASS
Search Index              PASS
Reports Summary           PASS
S7 (Multi-Tenancy)        SKIP
Where-Used API            PASS
BOM Compare               PASS
BOM Substitutes           PASS
Version-File Binding      PASS

PASS: 15  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run WU-1（Where-Used API 验收）

- 时间：`2025-12-19 11:27:17 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_where_used.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Assembly：`a12d031d-e94a-4b4d-9e77-e8579b6845fb`
  - Sub-Assembly：`142f0ecc-3903-4b76-b8ca-999fe5d8d002`
  - Component：`35b4f2b9-fa70-47d5-b24c-c8939a9b7d95`
  - Assembly2：`257ff0fe-c899-4c47-86c7-e3dd6971d606`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
Where-Used API Verification
...
Non-recursive where-used: OK (found 2 direct parents)
Recursive where-used: OK (found 3 parents)
Top-level item has no parents: OK
Non-existent item returns 404: OK

ALL CHECKS PASSED
```

## Run ALL-1（一键回归脚本：verify_all.sh）

- 时间：`2025-12-19 11:27:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=7, FAIL=0, SKIP=0)`
- 关键 ID（节选）：
  - Run H Part：`2bdaf336-efac-4842-bcd1-4293af42e825`
  - Run H RPC Part：`dcce484b-3b89-4df3-8c2a-167956a4e6fb`
  - Run H File：`8f619e13-a9cb-4f3a-952d-58e90039c8d1`
  - Run H ECO：`8411f267-8434-4e69-b190-bb6d6136124f`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Where-Used Component：`a77babbc-2a69-4832-b590-091843597187`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
REGRESSION TEST SUMMARY
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S5-A (CAD Pipeline S3)    PASS
Where-Used API            PASS

ALL TESTS PASSED
```

## Run ALL-2（一键回归脚本：verify_all.sh，BOM Compare 跳过）

- 时间：`2025-12-19 12:13:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=7, FAIL=0, SKIP=1)`
- 备注：`BOM Compare` 端点未上线，自动 SKIP
- 关键 ID（节选）：
  - Run H Part：`e0b411a4-226c-4a10-b7eb-cc83296d5ae5`
  - Run H RPC Part：`ef644c14-480a-4ca3-a082-96bb2377a460`
  - Run H File：`b438496d-1f78-424b-bd66-f32a35682737`
  - Run H ECO：`98acc423-2d09-4f38-8a54-0eda321263a8`
  - S5-A File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Where-Used Component：`a29e7a90-e457-4327-a7d1-bd1770061059`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Run H (Core APIs)         PASS
S1 (Meta + RBAC)          PASS
S3.1 (BOM Tree)           PASS
S3.2 (BOM Effectivity)    PASS
S3.3 (Versions)           PASS
S5-A (CAD Pipeline S3)    PASS
Where-Used API            PASS
BOM Compare               SKIP (endpoint not available)

PASS: 7  FAIL: 0  SKIP: 1

ALL TESTS PASSED
```

## Run H（全功能验证重跑：scripts/verify_run_h.sh）

- 时间：`2025-12-19 09:18:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_run_h.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`66587221-6128-4141-a695-622501757f98`
  - RPC Part：`af0e7d84-0f05-4d99-aa2c-bc4c7653505f`
  - File：`2665fb44-01bf-4186-ae28-9595cc380dea`
  - ECO Stage：`b60d8f66-d93a-40ce-8d7f-8e99c03c4e45`
  - ECO：`6546252b-974b-4b91-864f-fff07bfdfd63`
  - Version：`5b91648b-17c3-43ce-ae90-fa1e6412cd7d`

执行命令：

```bash
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出：

```text
==> Seed identity/meta
==> Login
==> Health
Health: OK
==> Meta metadata (Part)
Meta metadata: OK
==> AML add/get
AML add: OK (part_id=66587221-6128-4141-a695-622501757f98)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=af0e7d84-0f05-4d99-aa2c-bc4c7653505f)
==> File upload/download
File upload: OK (file_id=2665fb44-01bf-4186-ae28-9595cc380dea)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=b60d8f66-d93a-40ce-8d7f-8e99c03c4e45)
ECO create: OK (eco_id=6546252b-974b-4b91-864f-fff07bfdfd63)
ECO new-revision: OK (version_id=5b91648b-17c3-43ce-ae90-fa1e6412cd7d)
ECO approve: OK
ECO apply: OK
==> Versions history/tree
Versions history: OK
Versions tree: OK
==> Integrations health (should be 200 even if services down)
Integrations health: OK (ok=False)

ALL CHECKS PASSED
```

---

## Run PD-1（docker compose：PostgreSQL + MinIO(S3)）

- 时间：`2025-12-19 00:05:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 数据库：PostgreSQL（docker），宿主机端口 `55432`
- 对象存储：MinIO（docker），宿主机端口 `59000`（S3 API）/ `59001`（Console）
- 关键差异：S3 模式下载为 `302 -> 200`（presigned URL）

### 执行命令

```bash
docker compose up --build -d

export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations

bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 输出（摘要）

```text
==> Seed identity/meta
==> Login
==> Health
Health: OK
==> Meta metadata (Part)
Meta metadata: OK
==> AML add/get
AML add: OK (part_id=a2d194d4-dee1-4b9c-829a-47c0e19c0465)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=866d34c7-1004-47fd-aa8d-a59479848213)
==> File upload/download
File upload: OK (file_id=3366981d-567a-44ae-8aa3-e39296420065)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK
ECO create: OK
ECO new-revision: OK
ECO approve: OK
ECO apply: OK
==> Versions history/tree
Versions history: OK
Versions tree: OK
==> Integrations health (should be 200 even if services down)
Integrations health: OK (ok=False)

ALL CHECKS PASSED
```

---

## Run PD-2（Job 并发安全：2 worker / 10 jobs）

- 时间：`2025-12-19 00:19:10 +0800`
- 场景：docker compose（PostgreSQL + MinIO），`worker` 扩到 2 个实例
- 断言：10 个 job 全部 `completed`，且每个 job 的 `attempt_count == 1`

### 命令（摘要）

```bash
docker compose up -d --scale worker=2

# 创建 10 个 job（需要 admin token）
curl -X POST http://127.0.0.1:7910/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'content-type: application/json' \
  -d '{"task_type":"cad_conversion","payload":{"input_file_path":"part_a.dwg","output_format":"gltf"}}'

# 轮询 /api/v1/jobs/{id} 直到全部 completed，并检查 attempt_count==1
```

### 3) Switch Org（签发包含 org_id 的新 Token，已脱敏）

```bash
TOKEN='<redacted>'
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/switch-org \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"org_id":"org-1"}'
```

```json
{"access_token":"<redacted>","token_type":"bearer","expires_in":3600,"tenant_id":"tenant-1","user_id":1}
```

### 4) Jobs（不传 x-org-id，由 Token 的 org_id 决定）

```bash
ORG_TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/jobs \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $ORG_TOKEN"
```

```http
HTTP/1.1 200 OK
```

---

## Run B（AUTH_MODE=required，全局强制鉴权）

- 时间：`2025-12-18 13:26:16 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`43446`（见 `yuantus.pid`）
- 请求头：
  - `x-tenant-id: tenant-1`
  - `x-org-id: org-1`
- 说明：除 `GET /api/v1/health`、`POST /api/v1/auth/login`（以及 `/docs`/`/openapi.json`）外，其它接口必须带 `Authorization: Bearer <token>`（token 已脱敏）。

### 1) Health（无需 Token）

```bash
curl -s -i http://127.0.0.1:7910/api/v1/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```http
HTTP/1.1 200 OK
```

```json
{"ok":true,"service":"yuantus-plm","version":"0.1.0","tenant_id":"tenant-1","org_id":"org-1"}
```

### 2) Jobs（无 Token → 401）

```bash
curl -s -i http://127.0.0.1:7910/api/v1/jobs \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```http
HTTP/1.1 401 Unauthorized
```

```json
{"detail":"Missing bearer token"}
```

### 3) Login（获取 Token，已脱敏）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}'
```

```json
{"access_token":"<redacted>","token_type":"bearer","expires_in":3600,"tenant_id":"tenant-1","user_id":1}
```

### 4) Jobs（带 Token → 200）

```bash
TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/jobs \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN"
```

```http
HTTP/1.1 200 OK
```

```json
{"total":1,"items":[{"id":"6b3647e3-c41a-4a50-80ac-485be52e9bd1","task_type":"cad_conversion","payload":{"input_file_path":"part_a.dwg","output_format":"gltf"},"status":"completed","priority":10,"worker_id":"worker-verify","attempt_count":1,"max_attempts":3,"last_error":null,"created_at":"2025-12-18T03:38:19.801102","scheduled_at":"2025-12-18T03:38:19.801104","started_at":"2025-12-18T03:40:00.037505","completed_at":"2025-12-18T03:40:04.551959","created_by_id":1}]}
```

### 5) Tenant mismatch（401）

```bash
TOKEN='<redacted>'
curl -s -i http://127.0.0.1:7910/api/v1/jobs \
  -H 'x-tenant-id: tenant-2' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN"
```

```http
HTTP/1.1 401 Unauthorized
```

```json
{"detail":"Tenant mismatch"}
```

---

## Run A（AUTH_MODE=optional，旧验证）

- 时间：`2025-12-18 12:19:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 服务进程 PID：`28969`（历史记录）
- 请求头：
  - `x-tenant-id: tenant-1`
  - `x-org-id: org-1`

---

## 1) Health

```bash
curl -s -i http://127.0.0.1:7910/api/v1/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```http
HTTP/1.1 200 OK
```

```json
{"ok":true,"service":"yuantus-plm","version":"0.1.0","tenant_id":"tenant-1","org_id":"org-1"}
```

## 2) Plugins（列表 + Demo 路由）

```bash
curl -s http://127.0.0.1:7910/api/v1/plugins \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"ok":true,"plugins":[{"id":"yuantus-demo","name":"Yuantus Demo Plugin","version":"0.1.0","description":"Demo plugin that adds a simple API route.","author":"YuantusPLM","status":"active","is_active":true,"plugin_type":"extension","category":"demo","tags":["demo","plugin"],"dependencies":[],"loaded_at":"2025-12-18T02:33:05.258388+00:00","activated_at":"2025-12-18T02:33:05.258396+00:00","error_count":0,"last_error":null,"plugin_path":"plugins/yuantus-demo"}],"stats":{"total":1,"by_status":{"active":1},"by_type":{"extension":1},"by_category":{"demo":1},"errors":0}}
```

```bash
curl -s http://127.0.0.1:7910/api/v1/plugins/demo/ping \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"ok":true,"plugin":"yuantus-demo"}
```

## 3) Meta（Part 字段定义）

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/metadata/Part \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"id":"Part","label":"Part","is_relationship":false,"properties":[{"name":"item_number","label":"Part Number","type":"string","required":true,"length":32,"default":null},{"name":"name","label":"Name","type":"string","required":false,"length":128,"default":null},{"name":"description","label":"Description","type":"string","required":false,"length":256,"default":null},{"name":"state","label":"State","type":"string","required":false,"length":null,"default":"New"},{"name":"cost","label":"Cost","type":"float","required":false,"length":null,"default":null},{"name":"weight","label":"Weight","type":"float","required":false,"length":null,"default":null}]}
```

## 4) AML + Search（创建 Part + 检索）

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-VERIFY-105010","name":"Verify Part"}}'
```

```json
{"id":"7fad9a6a-9409-492a-880f-b65138386dc6","type":"Part","status":"created"}
```

```bash
curl -s 'http://127.0.0.1:7910/api/v1/search/?q=P-VERIFY&item_type=Part' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"hits":[{"id":"969300ca-35ce-43b1-8a4a-bb28638f640a","item_type_id":"Part","config_id":"dfc57cae-5c95-4ddf-bfb8-93ec94db9f46","state":"New","created_at":"2025-12-18T01:10:42","updated_at":"2025-12-18T01:11:49","properties":{"item_number":"P-VERIFY-0001","name":"Verify Part","state":"New"}},{"id":"77c7fb1d-cd3a-4459-90d9-9d394f60e6ae","item_type_id":"Part","config_id":"c638bc9d-b80b-4141-aace-040774c03cae","state":"New","created_at":"2025-12-18T01:11:01","updated_at":null,"properties":{"item_number":"P-VERIFY-0002","name":"Verify RPC Part","state":"New"}},{"id":"7fad9a6a-9409-492a-880f-b65138386dc6","item_type_id":"Part","config_id":"1b4a752f-330b-4eed-8bf6-bf1ba698cfab","state":"New","created_at":"2025-12-18T02:50:10","updated_at":null,"properties":{"item_number":"P-VERIFY-105010","name":"Verify Part","state":"New"}}],"total":3}
```

## 5) Versions（init）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/versions/items/7fad9a6a-9409-492a-880f-b65138386dc6/init \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"id":"7b3466b7-e810-45e9-b6b3-02987b259f67","item_id":"7fad9a6a-9409-492a-880f-b65138386dc6","generation":1,"revision":"A","version_label":"1.A","state":"Draft","is_current":true,"is_released":false,"properties":{"item_number":"P-VERIFY-105010","name":"Verify Part","state":"New"},"created_by_id":1,"created_at":"2025-12-18T02:51:15.631003","branch_name":"main","file_count":0}
```

## 6) File（上传 + 挂载）

```bash
curl -s 'http://127.0.0.1:7910/api/v1/file/upload?generate_preview=false' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F 'file=@/tmp/yuantus_upload_test.txt;filename=yuantus_upload_test.txt'
```

```json
{"id":"0a69d0e1-c672-4fe9-85bf-48b9e3fe3253","filename":"yuantus_upload_test.txt","url":"/api/v1/file/0a69d0e1-c672-4fe9-85bf-48b9e3fe3253/download","size":31,"mime_type":"text/plain","is_cad":false,"preview_url":null}
```

```bash
curl -s http://127.0.0.1:7910/api/v1/file/attach \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"item_id":"7fad9a6a-9409-492a-880f-b65138386dc6","file_id":"0a69d0e1-c672-4fe9-85bf-48b9e3fe3253","file_role":"attachment","description":"verify attach"}'
```

```json
{"status":"created","id":"68f64bf5-a3e1-4c39-a45e-d72cf145a992"}
```

## 7) ECO（最小闭环：创建 → new-revision → approve → apply）

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"ECO-VERIFY-105236","eco_type":"bom","product_id":"7fad9a6a-9409-492a-880f-b65138386dc6","description":"verify eco","priority":"normal"}'
```

```json
{"id":"0e1daf48-d631-4d42-82f5-bdd85f2afec2","name":"ECO-VERIFY-105236","eco_type":"bom","product_id":"7fad9a6a-9409-492a-880f-b65138386dc6","source_version_id":null,"target_version_id":null,"stage_id":"a705ae1d-5631-47d9-880d-8b5ae5e4dcfd","state":"draft","kanban_state":"normal","priority":"normal","description":"verify eco","product_version_before":null,"product_version_after":null,"effectivity_date":null,"created_by_id":1,"created_at":"2025-12-18T02:52:36.768355","updated_at":"2025-12-18T02:52:36.769857"}
```

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/0e1daf48-d631-4d42-82f5-bdd85f2afec2/new-revision' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"success":true,"version_id":"50ad62b5-a712-4ef0-a946-1003090d08f4","version_label":"1.A-eco-0e1daf48"}
```

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/0e1daf48-d631-4d42-82f5-bdd85f2afec2/approve' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"comment":"verify approve"}'
```

```json
{"id":"ec6c337c-d6d0-42a5-a77c-6f85be696d6f","eco_id":"0e1daf48-d631-4d42-82f5-bdd85f2afec2","stage_id":"a705ae1d-5631-47d9-880d-8b5ae5e4dcfd","approval_type":"mandatory","required_role":null,"user_id":1,"status":"approved","comment":"verify approve","approved_at":"2025-12-18T02:53:01.679336","created_at":"2025-12-18T02:53:01.679778"}
```

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/0e1daf48-d631-4d42-82f5-bdd85f2afec2/apply' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"success":true,"message":"ECO applied successfully"}
```

验证 current_version_id：

```bash
curl -s http://127.0.0.1:7910/api/v1/bom/7fad9a6a-9409-492a-880f-b65138386dc6/effective \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"current_version_id":"50ad62b5-a712-4ef0-a946-1003090d08f4"}
```

## 8) Integrations（聚合健康）

```bash
curl -s http://127.0.0.1:7910/api/v1/integrations/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"ok":false,"tenant_id":"tenant-1","org_id":"org-1","services":{"athena":{"ok":false,"base_url":"http://localhost:7700/api/v1","status_code":401,"error":""},"cad_ml":{"ok":false,"base_url":"http://localhost:8001","error":"All connection attempts failed"},"dedup_vision":{"ok":false,"base_url":"http://localhost:8100","error":"All connection attempts failed"}}}
```

## 9) Jobs + Worker（创建 Job → Worker 执行 → 状态 completed）

创建 Job：

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/jobs' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"task_type":"cad_conversion","payload":{"input_file_path":"part_a.dwg","output_format":"gltf"},"priority":10}'
```

```json
{"id":"6b3647e3-c41a-4a50-80ac-485be52e9bd1","task_type":"cad_conversion","payload":{"input_file_path":"part_a.dwg","output_format":"gltf"},"status":"pending","priority":10,"worker_id":null,"attempt_count":0,"max_attempts":3,"last_error":null,"created_at":"2025-12-18T03:38:19.801102","scheduled_at":"2025-12-18T03:38:19.801104","started_at":null,"completed_at":null,"created_by_id":1}
```

执行 Worker（一次）：

```bash
yuantus worker --worker-id worker-verify --poll-interval 1 --once
```

```text
Processed one job.
```

查询状态：

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/6b3647e3-c41a-4a50-80ac-485be52e9bd1 \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"id":"6b3647e3-c41a-4a50-80ac-485be52e9bd1","task_type":"cad_conversion","payload":{"input_file_path":"part_a.dwg","output_format":"gltf"},"status":"completed","priority":10,"worker_id":"worker-verify","attempt_count":1,"max_attempts":3,"last_error":null,"created_at":"2025-12-18T03:38:19.801102","scheduled_at":"2025-12-18T03:38:19.801104","started_at":"2025-12-18T03:40:00.037505","completed_at":"2025-12-18T03:40:04.551959","created_by_id":1}
```

## 10) Auth（seed → login → orgs）

Seed（dev）：

```bash
yuantus seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin,engineer
```

```text
Seeded identity: tenant=tenant-1, org=org-1, user=admin (1)
```

Login：

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}'
```

```json
{"access_token":"<redacted>","token_type":"bearer","expires_in":3600,"tenant_id":"tenant-1","user_id":1}
```

List orgs：

```bash
TOKEN='<access_token>'
curl -s http://127.0.0.1:7910/api/v1/auth/orgs -H "Authorization: Bearer $TOKEN"
```

```json
{"tenant_id":"tenant-1","user_id":1,"orgs":[{"id":"org-1","name":"org-1","is_active":true}]}
```

## Run BC-3（BOM Compare 含生效与替代件）

- 时间：`2025-12-21 12:34:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`3cf426b5-8002-4b4e-855d-223b808aa74e`
  - Parent B：`19718808-a3b7-4812-9fc2-8fc934eff993`
  - Child X：`fd785fde-4bb0-495c-b541-97c65067547b`
  - Child Y：`82d53fbc-753a-4e2b-92e3-7e2fd90f7258`
  - Child Z：`6e3ee964-10c9-4548-b7f7-44a1c08e97cf`

执行命令：

```bash
# 重建 API/worker 以加载最新 BOM Compare 逻辑
docker compose -p yuantusplm up -d --build

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
ALL CHECKS PASSED
```

## Run S5-B-3（CAD 2D Connectors：Haochen/Zhongwang aliases）

- 时间：`2025-12-21 12:34:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`4aa92285-d18b-450f-8628-dd0693d17a79`
  - ZWCAD File：`0367a7e8-4a53-4269-8243-f64defb3a584`
  - Haochen Alias File：`fc4ffab2-a930-4567-a4d0-b6d231b93165`
  - Zhongwang Alias File：`dfa6863f-c8bb-425b-92be-7d086dc17004`

执行命令：

```bash
bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run ALL-12（一键回归脚本：verify_all.sh，含属性归一化）

- 时间：`2025-12-26 08:26:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：PASS=39 / FAIL=0 / SKIP=0

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg'
export YUANTUS_AUTH_MODE=required
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=1

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 39  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run ALL-18（一键回归脚本：verify_all.sh，含失败项）

- 时间：`2025-12-21 12:47:17 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`REGRESSION FAILED (PASS=11, FAIL=4, SKIP=2)`
- 失败项：
  - S1 (Meta + RBAC)：viewer 写操作返回 200（期望 403）
  - S3.2 (BOM Effectivity)：viewer 写操作返回 200；删除后 NEXT_WEEK 仍返回 2 条
  - S4 (ECO Advanced)：viewer 登录失败（无 access_token）
  - S5-C (CAD Attribute Sync)：job 状态停留在 processing
- 跳过项：
  - Audit Logs（audit_enabled=false）
  - S7 (Multi-Tenancy)（tenancy_mode=single）

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 11  FAIL: 4  SKIP: 2
REGRESSION FAILED
```

## Run ALL-19（一键回归脚本：verify_all.sh，DB_URL 自动探测）

- 时间：`2025-12-21 13:00:43 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=15, FAIL=0, SKIP=2)`
- 跳过项：
  - Audit Logs（audit_enabled=false）
  - S7 (Multi-Tenancy)（tenancy_mode=single）

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 15  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```

## Run ALL-20（一键回归脚本：verify_all.sh，Audit Logs enabled）

- 时间：`2025-12-21 13:42:02 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=16, FAIL=0, SKIP=1)`
- 跳过项：
  - S7 (Multi-Tenancy)（tenancy_mode=single）

执行命令：

```bash
YUANTUS_AUDIT_ENABLED=true docker compose -p yuantusplm -f docker-compose.yml up -d --build
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 16  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```

## Run S7-1（Multi-Tenancy：db-per-tenant-org）

- 时间：`2025-12-21 13:39:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
docker compose -p yuantusplm -f docker-compose.yml -f docker-compose.mt.yml up -d --build
MODE=db-per-tenant-org DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
Multi-Tenancy Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-4（CAD 2D Connectors：cad_connector_id）

- 时间：`2025-12-21 15:31:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`470cb8aa-cc0a-4543-94e9-751549c7779e`
  - ZWCAD File：`167bf590-a955-4967-9e40-e58f26ab2d2f`
  - Haochen Alias File：`c4b81ad0-ef64-43d2-bf72-c2c0b268f40a`
  - Zhongwang Alias File：`faac3a03-6743-4d0e-8897-2919e851a1f7`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-5（CAD 2D Connectors：auto-detect by content）

- 时间：`2025-12-23 13:59:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`cd5be06c-755e-4072-b53d-ed7016d5b9ee`
  - ZWCAD File：`38286688-9cee-4968-b052-10ce25d41bee`
  - Haochen File：`f97dea62-8c2d-4d37-9767-d5305487f344`
  - Zhongwang File：`aa0ebbf7-63d6-4a04-8f91-3607ade231ac`
  - Auto-detect File：`46a7cf35-ebb7-4ed7-aab4-39717a61054b`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run S5-A-4（CAD Pipeline S3）

- 时间：`2025-12-21 15:31:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_pipeline_s3.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Preview Job：`2c2af0fb-b9ef-40dc-a547-69dfc3b4f8e6`
  - Geometry Job：`8749f6a9-34c4-4bbf-ba47-9b30de716063`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Pipeline S3 Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-2（CAD Attribute Sync：cad_extract）

- 时间：`2025-12-21 16:30:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`1e29e819-e6f6-4f56-a79e-d2569f8461aa`
  - File：`4e25ecad-e484-44c5-861b-01435d77cee8`
  - Job：`fb57a93f-cc4d-4c44-82a8-4a36e97c2972`

执行命令：

```bash
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Attribute Sync Verification Complete
ALL CHECKS PASSED
```

## Run ALL-47（一键回归：verify_all.sh + 多租户 + CAD Extractor）

- 时间：`2025-12-24 14:14:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`
- 依赖：`cad-extractor` 运行中（`http://127.0.0.1:8200`）
- 结果：`PASS=27, FAIL=0, SKIP=0`
- 说明：`docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build`

执行命令：

```bash
. .venv/bin/activate
YUANTUS_TENANCY_MODE='db-per-tenant-org' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 27  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run S5-B-Connectors-Config（自定义 CAD 连接器配置）

- 时间：`2025-12-24 14:22:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`（CLI 以 `single` 直连 tenant DB）
- 结果：`ALL CHECKS PASSED`
- 关键 ID：`file_id=3809b563-91d1-4c10-893b-e412eedb9d89`

执行命令：

```bash
YUANTUS_TENANCY_MODE='single' \
YUANTUS_DATABASE_URL_TEMPLATE='' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE='s3' \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
  bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Connectors Config Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-SyncTemplate（CAD Sync Template）

- 时间：`2025-12-24 14:22:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`（CLI 以 `single` 直连 tenant DB）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
YUANTUS_TENANCY_MODE='single' \
YUANTUS_DATABASE_URL_TEMPLATE='' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE='s3' \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
  bash scripts/verify_cad_sync_template.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Sync Template Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-Stub（外部提取 stub）

- 时间：`2025-12-24 14:22:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`（CLI 以 `single` 直连 tenant DB）
- 结果：`ALL CHECKS PASSED`
- 关键 ID：`file_id=cf7efbf1-723f-466a-ad47-6b616c6e7fd1`, `job_id=85b6fd69-e33d-4e17-9dc1-d5d2222c5b36`

执行命令：

```bash
YUANTUS_TENANCY_MODE='single' \
YUANTUS_DATABASE_URL_TEMPLATE='' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE='s3' \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
  bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor Stub Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External（真实 DWG 外部提取）

- 时间：`2025-12-24 14:22:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- 外部服务：`http://127.0.0.1:8200`
- 样例文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：`file_id=46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`, `job_id=6e1bcd0c-b5a1-48b8-8fc9-98969b0de904`

执行命令：

```bash
YUANTUS_TENANCY_MODE='single' \
YUANTUS_DATABASE_URL_TEMPLATE='' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE='s3' \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run Backup-Restore（私有化备份/恢复）

- 时间：`2025-12-24 14:29:22 +0800`
- 结果：`ALL CHECKS PASSED`
- 关键路径：
  - 备份目录：`/tmp/yuantus_backup_verify_1766557724`
  - 恢复数据库后缀：`_restore_1766557724`
  - 恢复桶：`yuantus-restore-test-1766557724`
- 说明：使用已运行的 `yuantus` docker compose 项目（避免端口冲突）

执行命令：

```bash
PROJECT=yuantus bash scripts/verify_backup_restore.sh
```

输出（摘要）：

```text
Backup/Restore Verification Complete
ALL CHECKS PASSED
```

## Run Cleanup-Restore（清理恢复残留）

- 时间：`2025-12-24 14:29:22 +0800`
- 结果：`ALL CHECKS PASSED`
- 关键资源：
  - 测试数据库：`yuantus_cleanup_test_1766557747`
  - 测试桶：`yuantus-cleanup-test-1766557747`

执行命令：

```bash
PROJECT=yuantus bash scripts/verify_cleanup_restore.sh
```

输出（摘要）：

```text
Cleanup Verification Complete
ALL CHECKS PASSED
```

## Run Backup-Rotation（备份轮转）

- 时间：`2025-12-24 14:29:22 +0800`
- 结果：`ALL CHECKS PASSED`
- 说明：保持最新 2 个备份

执行命令：

```bash
bash scripts/verify_backup_rotation.sh
```

输出（摘要）：

```text
Rotation kept newest 2
ALL CHECKS PASSED
```

## Run ALL-48（一键回归：verify_all.sh + CAD Extractor 全量）

- 时间：`2025-12-24 14:31:37 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`
- 结果：`PASS=31, FAIL=0, SKIP=0`
- 说明：启用 CAD Extractor Stub/External/Service + CAD Auto Part

执行命令：

```bash
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
RUN_CAD_EXTRACTOR_STUB=1 \
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 31  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run S6-Search-Index（搜索索引增量）

- 时间：`2025-12-24 14:45:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`（CLI 以 `single` 直连 tenant DB）
- 结果：`ALL CHECKS PASSED`
- 关键 ID：`part_id=d8ea3be2-3b12-4355-bf62-9c64954f7bfd`

执行命令：

```bash
YUANTUS_TENANCY_MODE='single' \
YUANTUS_DATABASE_URL_TEMPLATE='' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_search_index.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Search Index Verification Complete
ALL CHECKS PASSED
```

## Run S6-Search-Reindex（索引状态 + 重建）

- 时间：`2025-12-24 14:45:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- Engine：`db`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：`part_id=de805297-f782-495e-84db-6973f607dc1b`, `indexed=106`

执行命令：

```bash
YUANTUS_TENANCY_MODE='single' \
YUANTUS_DATABASE_URL_TEMPLATE='' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_search_reindex.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Search Reindex Verification Complete
ALL CHECKS PASSED
```

## Run ALL-43（一键回归：verify_all.sh + CAD Auto Part + CAD Extractor Service）

- 时间：`2025-12-24 08:48:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`（PASS=27, FAIL=0, SKIP=0）
- 说明：`S5-C (CAD Auto Part)` 与 `S5-C (CAD Extractor Service)` 均通过；脚本检测到已运行的 CAD Extractor 服务并自动设置 `START_SERVICE=0`。

执行命令：

```bash
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 27  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run Compose-No-CAD-Extractor（Compose 配置校验）

- 时间：`2025-12-24 13:54:19 +0800`
- 结果：`config ok`

执行命令：

```bash
docker compose -f docker-compose.yml -f docker-compose.no-cad-extractor.yml config
```

## Run Compose-No-CAD-Extractor-Startup（轻量启动验证）

- 时间：`2025-12-24 13:58:23 +0800`
- 结果：`api/worker/minio/postgres/redis` 启动成功，`cad-extractor` 未启动

执行命令：

```bash
docker compose -f docker-compose.yml -f docker-compose.no-cad-extractor.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.no-cad-extractor.yml ps
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:7910/api/v1/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

输出（摘要）：

```text
api: Up (healthy)
worker: Up
postgres: Up (healthy)
minio: Up (healthy)
redis: Up
health: 200
```

## Run ALL-46（轻量模式回归：no cad-extractor）

- 时间：`2025-12-24 14:05:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`（PASS=25, FAIL=0, SKIP=2）
- 说明：轻量启动（`docker-compose.no-cad-extractor.yml`），跳过 `S5-C (CAD Extractor Service)` 与 `S7 (Multi-Tenancy)`

执行命令：

```bash
. .venv/bin/activate
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=0 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 25  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```

## Run ALL-45（一键回归：verify_all.sh + CAD Auto Part + CAD Extractor Service）

- 时间：`2025-12-24 13:05:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`（PASS=27, FAIL=0, SKIP=0）
- 说明：使用 Python 3.11 虚拟环境运行（不再出现 boto3 3.9 弃用告警）

执行命令：

```bash
. .venv/bin/activate
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 27  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run CAD-Extractor-Compose-Healthcheck（Docker Compose 健康检查）

- 时间：`2025-12-24 08:57:01 +0800`
- 服务：`cad-extractor`
- 结果：`healthy`

执行命令：

```bash
docker compose -p yuantusplm up -d --build cad-extractor
docker compose -p yuantusplm ps cad-extractor
```

输出（摘要）：

```text
STATUS: Up (healthy)
PORTS: 0.0.0.0:8200->8200/tcp
```

## Run Compose-CAD-Extractor-Dependency（API/Worker 依赖 CAD Extractor）

- 时间：`2025-12-24 09:02:43 +0800`
- 结果：`cad-extractor/api/worker` 启动成功，`cad-extractor` 健康检查通过

执行命令：

```bash
docker compose -p yuantusplm up -d --build
docker compose -p yuantusplm ps
```

输出（摘要）：

```text
api: Up (healthy)
cad-extractor: Up (healthy)
worker: Up
postgres: Up (healthy)
minio: Up (healthy)
```

## Run ALL-44（一键回归：verify_all.sh + CAD Auto Part + CAD Extractor Service）

- 时间：`2025-12-24 12:15:07 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`（PASS=27, FAIL=0, SKIP=0）
- 说明：`S5-C (CAD Auto Part)` 与 `S5-C (CAD Extractor Service)` 均通过

执行命令：

```bash
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 27  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```
## Run ALL-42（一键回归：verify_all.sh + CAD Auto Part + CAD Extractor Service）

- 时间：`2025-12-24 08:43:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`（PASS=27, FAIL=0, SKIP=0）
- 说明：`S5-C (CAD Auto Part)` 与 `S5-C (CAD Extractor Service)` 均通过；脚本检测到已运行的 CAD Extractor 服务并自动设置 `START_SERVICE=0`。

执行命令：

```bash
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 27  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run ALL-41（一键回归：verify_all.sh + CAD Auto Part 通过）

- 时间：`2025-12-24 08:28:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`（PASS=26, FAIL=0, SKIP=1）
- 说明：`S5-C (CAD Auto Part)` 已通过；`S5-C (CAD Extractor Service)` 未开启（RUN_CAD_EXTRACTOR_SERVICE=0）

执行命令：

```bash
RUN_CAD_AUTO_PART=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 26  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```

## Run S5-C-Extractor-Service-2（CAD Extractor Service Script）

- 时间：`2025-12-24 08:34:21 +0800`
- 基地址：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_service.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：健康检查自动检测到已运行服务，脚本将 `START_SERVICE` 置为 `0`

执行命令：

```bash
START_SERVICE=0 \
  bash scripts/verify_cad_extractor_service.sh http://127.0.0.1:8200
```

输出（摘要）：

```text
CAD Extractor Service Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-RealDWG-AutoPart（真实 DWG + auto_create_part）

- 时间：`2025-12-23 23:37:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_auto_part.sh`
- 结果：`ALL CHECKS PASSED`
- 样例文件与关键 ID：
  - `J2824002-06上封头组件v2.dwg` → `item_number=J2824002-06`, `revision=v2`
    - Part：`ac005a45-af28-4e89-9ae5-29d6b688bac8`
    - File：`40021aa5-b21a-43a3-a519-28fafaea879e`
    - Attachment：`3b8d09fb-dc7a-4067-8354-a7d6ce10432a`
  - `J2825002-09下轴承支架组件v2.dwg` → `item_number=J2825002-09`, `revision=v2`
    - Part：`d6079242-54d0-4142-a2c1-d99c01ab0369`
    - File：`c8fb59d5-7c42-4cd2-822e-20d75be79abb`
    - Attachment：`98781ce3-9ba2-4db6-abeb-3afa3b7314d0`
  - `J0724006-01下锥体组件v3.dwg` → `item_number=J0724006-01`, `revision=v3`
    - Part：`fc9b73c0-a32f-49a8-a47f-0a21b11b6283`
    - File：`b8904af3-2f3a-4864-bb34-17521dbdf5d9`
    - Attachment：`da718f9c-752f-446b-a246-1689fe1b5183`

执行命令（示例）：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

CAD_AUTO_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_AUTO_EXPECT_ITEM_NUMBER='J2824002-06' \
CAD_AUTO_EXPECT_REVISION='v2' \
  bash scripts/verify_cad_auto_part.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Auto Part Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-Stub-2（CAD Extractor Stub）

- 时间：`2025-12-24 16:39:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_stub.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`cf7efbf1-723f-466a-ad47-6b616c6e7fd1`
  - Job：`53291cae-ce26-4ae9-a33e-0529297d20c8`
- Extractor：`http://127.0.0.1:63135`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'

bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor Stub Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-LOCAL-4（CAD Extract Local Verification）

- 时间：`2025-12-24 16:39:49 +0800`
- 脚本：`scripts/verify_cad_extract_local.sh`
- 结果：`ALL CHECKS PASSED`
- DB：`/tmp/yuantus_cad_extract_local.db`
- Storage：`/tmp/yuantus_cad_extract_storage`

执行命令：

```bash
bash scripts/verify_cad_extract_local.sh
```

输出（摘要）：

```text
CAD Extract Local Verification Complete
ALL CHECKS PASSED
```

## Run ALL-10（一键回归脚本：verify_all.sh）

- 时间：`2025-12-26 00:14:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：PASS=33 / FAIL=0 / SKIP=5
- SKIP 项：
  - `S5-C (CAD Auto Part)`：`RUN_CAD_AUTO_PART=0`
  - `S5-C (CAD Extractor Stub)`：`RUN_CAD_EXTRACTOR_STUB=0`
  - `S5-C (CAD Extractor External)`：`RUN_CAD_EXTRACTOR_EXTERNAL=0`
  - `S5-C (CAD Extractor Service)`：`RUN_CAD_EXTRACTOR_SERVICE=0`
  - `S7 (Tenant Provisioning)`：`RUN_TENANT_PROVISIONING=0`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 33  FAIL: 0  SKIP: 5
ALL TESTS PASSED
```

## Run ALL-11（一键回归脚本：verify_all.sh，启用全部可选项）

- 时间：`2025-12-26 00:22:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：PASS=38 / FAIL=0 / SKIP=0
- 备注：Tenant Provisioning 返回 `SKIP: platform admin disabled`（脚本退出码为 0）

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg'
export YUANTUS_AUTH_MODE=required
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=1

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 38  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run S5-C-RealDWG-AutoPart-2（脚本自动探测 DB/租户环境）

- 时间：`2025-12-24 00:00:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_auto_part.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：无需显式传 `YUANTUS_TENANCY_MODE/DB_URL_TEMPLATE/IDENTITY_DB_URL`，脚本自动探测
- 样例文件与关键 ID：
  - `J2824002-06上封头组件v2.dwg` → `item_number=J2824002-06`, `revision=v2`
    - Part：`ac005a45-af28-4e89-9ae5-29d6b688bac8`
    - File：`40021aa5-b21a-43a3-a519-28fafaea879e`
    - Attachment：`3b8d09fb-dc7a-4067-8354-a7d6ce10432a`

执行命令（示例）：

```bash
CAD_AUTO_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_AUTO_EXPECT_ITEM_NUMBER='J2824002-06' \
CAD_AUTO_EXPECT_REVISION='v2' \
  bash scripts/verify_cad_auto_part.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Auto Part Verification Complete
ALL CHECKS PASSED
```


## Run S5-C-3（CAD Attribute Sync：cad_extract + attributes endpoint）

- 时间：`2025-12-21 18:11:32 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`460fdbbf-3dd7-4337-8f43-bb09df0e07fb`
  - File：`4e25ecad-e484-44c5-861b-01435d77cee8`
  - Job：`9923e63d-617b-47f8-b36b-31e1ab64fa31`

执行命令：

```bash
YUANTUS_STORAGE_TYPE=s3 YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 YUANTUS_S3_ACCESS_KEY_ID=minioadmin YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'   bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Attribute Sync Verification Complete
ALL CHECKS PASSED
```


## Run ALL-21（一键回归脚本：verify_all.sh，含 cad_extract）

- 时间：`2025-12-21 18:13:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=15, FAIL=0, SKIP=2)`
- 跳过项：
  - Audit Logs（audit_enabled=false）
  - S7 (Multi-Tenancy)（tenancy_mode=single）
- 关键 ID（S5-C）：
  - Item：`3be82f9b-e46b-4fc3-9e81-e3363acf3c93`
  - File：`4e25ecad-e484-44c5-861b-01435d77cee8`
  - Job：`b1c78b82-3b39-4d16-abe4-5ae0dd7a39aa`

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 15  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```


## Run S5-C-LOCAL-1（CAD Extract Local Verification）

- 时间：`2025-12-21 20:29:54 +0800`
- 脚本：`scripts/verify_cad_extract_local.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - PY：`.venv/bin/python`
  - PYTHONPATH：`src`
  - DB：`/tmp/yuantus_cad_extract_local.db`
  - Storage：`/tmp/yuantus_cad_extract_storage`
- 备注：`cadquery not installed`（已提示，未影响 cad_extract）

执行命令：

```bash
PY=.venv/bin/python PYTHONPATH=src bash scripts/verify_cad_extract_local.sh
```

输出（摘要）：

```text
CAD Extract Local Verification Complete
ALL CHECKS PASSED
```


## Run ALL-38（一键回归脚本：verify_all.sh，single + S3 env）

- 时间：`2025-12-23 14:22:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=23, FAIL=0, SKIP=2)`
- SKIP：Audit Logs（audit_enabled=false），Multi-Tenancy（tenancy_mode=single）
- 关键 ID：
  - Document：`eab43e0d-1803-46ef-9953-06070dbb3133`
  - Part (lifecycle)：`c14fe667-dde7-4a46-9658-326acba5f7e6`
  - CAD File (S5-A)：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`

执行命令：

```bash
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 23  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```


## Run S5-C-LOCAL-2（CAD Extract Local Verification，默认脚本）

- 时间：`2025-12-21 20:31:04 +0800`
- 脚本：`scripts/verify_cad_extract_local.sh`
- 结果：`ALL CHECKS PASSED`
- 环境（脚本默认解析）：
  - PY：`.venv/bin/python`
  - PYTHONPATH：`<repo>/src`
  - DB：`/tmp/yuantus_cad_extract_local.db`
  - Storage：`/tmp/yuantus_cad_extract_storage`
- 备注：`cadquery not installed`（已提示，未影响 cad_extract）

执行命令：

```bash
bash scripts/verify_cad_extract_local.sh
```

输出（摘要）：

```text
CAD Extract Local Verification Complete
ALL CHECKS PASSED
```


## Run ALL-22（一键回归脚本：verify_all.sh）

- 时间：`2025-12-21 20:50:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=15, FAIL=0, SKIP=2)`
- 跳过项：
  - Audit Logs（audit_enabled=false）
  - S7 (Multi-Tenancy)（tenancy_mode=single）
- 关键 ID（S5-C）：
  - Item：`f3b84ade-9474-42c4-96e9-3b8aa5089912`
  - File：`7557a108-5acd-443d-affe-1ce90d0654aa`
  - Job：`0d4b3dff-f335-461b-94ea-28242c6b1a50`

执行命令：

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 15  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```


## Run S7-1（Multi-Tenancy：db-per-tenant-org）

- 时间：`2025-12-21 21:24:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`

执行命令：

```bash
MODE=db-per-tenant-org DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'   bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
Multi-Tenancy Verification Complete
ALL CHECKS PASSED
```


## Run ALL-23（一键回归脚本：verify_all.sh，db-per-tenant-org）

- 时间：`2025-12-21 21:51:27 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=16, FAIL=0, SKIP=1)`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 跳过项：
  - Audit Logs（audit_enabled=false）
- 关键 ID（S5-C）：
  - Item：`0dfd3777-7be5-4390-8f9d-8bba326a99aa`
  - File：`88457b79-4551-40b4-965a-49c73b7e50a4`
  - Job：`26466c1a-36e2-4ecf-b6b3-95ec74b74b0f`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'   bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 16  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```

## Run AUDIT-RET-1（Audit Logs + Retention）

- 时间：`2025-12-21 22:23:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - AUDIT_RETENTION_MAX_ROWS：`5`
  - AUDIT_RETENTION_DAYS：`1`
  - AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS：`1`
  - DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`

执行命令：

```bash
AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Audit retention verified
ALL CHECKS PASSED
```

## Run AUDIT-RET-2（Audit Logs + Retention，db-per-tenant-org）

- 时间：`2025-12-23 13:29:44 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - AUDIT_RETENTION_MAX_ROWS：`5`
  - AUDIT_RETENTION_DAYS：`1`
  - AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS：`1`
  - DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`

执行命令：

```bash
AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Audit retention: OK
ALL CHECKS PASSED
```


## Run OPS-1（Ops Health）

- 时间：`2025-12-21 22:23:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_health.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_ops_health.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Health deps: OK
ALL CHECKS PASSED
```


## Run MT-MIGRATE-1（Multi-Tenant Migrations）

- 时间：`2025-12-21 22:23:05 +0800`
- 脚本：`scripts/mt_migrate.sh`
- 结果：`Migrations complete`
- 模式：`db-per-tenant-org`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- AUTO_STAMP：`1`

执行命令：

```bash
MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  ./scripts/mt_migrate.sh
```

输出（摘要）：

```text
Migrations complete.
```


## Run CAD-MISSING-1（CAD Missing Source）

- 时间：`2025-12-21 22:23:05 +0800`
- 基地址：`http://127.0.0.1:7912`
- 脚本：`scripts/verify_cad_missing_source.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - DB_URL：`sqlite:////tmp/yuantus_missing_source.db`
  - IDENTITY_DB_URL：`sqlite:////tmp/yuantus_missing_source_identity.db`
  - LOCAL_STORAGE_PATH：`/tmp/yuantus_missing_source_storage`
- 关键 ID：
  - File：`0d921a25-11f3-4d2e-93fc-e50a0088f8a8`
  - Job：`460d402e-5f62-4e00-bb43-830224a81d3a`

执行命令：

```bash
DB_URL='sqlite:////tmp/yuantus_missing_source.db' \
IDENTITY_DB_URL='sqlite:////tmp/yuantus_missing_source_identity.db' \
LOCAL_STORAGE_PATH='/tmp/yuantus_missing_source_storage' \
  bash scripts/verify_cad_missing_source.sh http://127.0.0.1:7912 tenant-1 org-1
```

输出（摘要）：

```text
Job failed without retries
ALL CHECKS PASSED
```


## Run S5-A-2（CAD Pipeline S3 Regression）

- 时间：`2025-12-21 22:23:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_pipeline_s3.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`a5033222-ec3c-4345-b54a-c5fa0de20cc3`
  - Preview Job：`16a36c52-891c-488e-bfa2-42b1423d7869`
  - Geometry Job：`a41fa0f3-37a9-44e0-8c4b-03336563fcb4`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Preview job status: completed
Geometry job status: completed
ALL CHECKS PASSED
```

## Run ALL-24（一键回归脚本：verify_all.sh，审计保留启用）

- 时间：`2025-12-22 08:27:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=17, FAIL=0, SKIP=1)`
- 跳过项：
  - S7 (Multi-Tenancy)（tenancy_mode=single）
- 审计保留：`max_rows=5, days=1, prune_interval=1`
- 关键 ID（S5-C）：
  - Item：`221526f7-4438-4469-a1f4-aff8c07f8d60`
  - File：`66c0612a-d883-473b-998b-610ebb9b8246`
  - Job：`91a8032b-e9eb-443b-a649-62b688d2997d`

执行命令：

```bash
AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 17  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```


## Run ALL-25（一键回归脚本：verify_all.sh，db-per-tenant-org）

- 时间：`2025-12-22 08:27:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=18, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB_URL_TEMPLATE：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- IDENTITY_DB_URL：`postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- 审计保留：`max_rows=5, days=1, prune_interval=1`
- 关键 ID（S5-C）：
  - Item：`dea34b65-8c98-4d6c-ad00-cadb0aba4482`
  - File：`9777a8d1-4f21-4c26-ba90-5d3fc055798e`
  - Job：`30fcaa80-2f42-4e2c-bc65-11118ea00553`

执行命令：

```bash
AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 18  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run S5-A-MT-2（CAD Pipeline S3，db-per-tenant-org 修复后）

- 时间：`2025-12-22 08:27:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_pipeline_s3.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`9a7dad67-2ac2-46f1-bbb7-b3119f48c533`
  - Preview Job：`02827d1f-77bf-43a6-bd63-089ed278554e`
  - Geometry Job：`d16e4bf3-3a6c-493c-8687-8d56348b938b`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Job processing: completed / completed
ALL CHECKS PASSED
```


## Run BC-4（BOM Compare：字段对照补充后复验）

- 时间：`2025-12-22 09:17:13 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`a3e92ccb-06fb-4f4e-81d2-b0fb7345d45f`
  - Parent B：`d702e82d-057e-4e43-a0fd-f76826482d62`
  - Child X：`0c8b475d-16a4-4552-b772-37a7ce5e0913`
  - Child Y：`f57ebfee-8721-4f0f-a5b4-35740b8a2680`
  - Child Z：`f34fa407-26a9-4f68-aab3-50752daecde0`
  - Substitute：`2022c357-25ce-4597-8e6b-f10b82b6f2cd`

执行命令：

```bash
bash scripts/verify_bom_compare.sh
```

输出（摘要）：

```text
BOM Compare: OK
ALL CHECKS PASSED
```


## Run DOC-1（Document Lifecycle 控制发布）

- 时间：`2025-12-23 09:02:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_document_lifecycle.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Document：`cba51d5c-6337-4c03-b86f-c8a66a1947ca`
  - Version：`1.A`

执行命令：

```bash
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_document_lifecycle.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```


## Run ALL-26（一键回归脚本：verify_all.sh，single 模式）

- 时间：`2025-12-23 09:13:48 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=22, FAIL=0, SKIP=2)`
- SKIP：Audit Logs（audit_enabled=false），Multi-Tenancy（tenancy_mode=single）
- 关键 ID：
  - Document：`8cd6fb88-b749-4b40-8ac4-0729563ec00d`
  - S2 File：`a619e60b-5154-40fc-8c12-d904edc018d3`
  - Run H File：`682eddc3-b17a-4ef4-ae52-ab7af7730ebf`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 22  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```


## Run ALL-27（一键回归脚本：verify_all.sh，audit + db-per-tenant-org）

- 时间：`2025-12-23 09:21:26 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=24, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- 审计：`enabled`
- 关键 ID：
  - Document：`58cce8b0-f1cc-4f5d-80e6-f31d293d7b6c`
  - Run H File：`52e33c24-5ea9-4ee1-b957-514c12784351`
  - S2 File：`2ed67ffa-eb45-4fbc-bcb1-6337084ff7f8`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_AUDIT_ENABLED=true \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 24  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run ALL-28（一键回归脚本：verify_all.sh，audit + db-per-tenant-org + Part Lifecycle）

- 时间：`2025-12-23 10:33:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=25, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- 审计：`enabled`
- 关键 ID：
  - Document：`44646439-2d64-42a7-b074-6a7fb639359e`
  - Part (lifecycle)：`9a69f018-2fe0-465c-be8b-c63cede0b105`
  - CAD File (S5-A)：`9a7dad67-2ac2-46f1-bbb7-b3119f48c533`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_AUDIT_ENABLED=true \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 25  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run ALL-29（一键回归脚本：verify_all.sh，db-per-tenant-org）

- 时间：`2025-12-23 13:21:43 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=25, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- 审计：`disabled`
- 关键 ID：
  - Document：`d7600cc4-f9bb-48dd-8bf5-0e9fb2345503`
  - Part (lifecycle)：`b1878353-b699-41f7-b872-79cdae2703b3`
  - CAD File (S5-A)：`9a7dad67-2ac2-46f1-bbb7-b3119f48c533`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 25  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run ALL-37（一键回归脚本：verify_all.sh，db-per-tenant-org + quota enforce + audit retention）

- 时间：`2025-12-23 13:33:37 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED (PASS=25, FAIL=0, SKIP=0)`
- 模式：`db-per-tenant-org`
- 审计：`enabled`（retention days=1, max_rows=5, prune_interval=1）
- 配额：`enforce`
- 关键 ID：
  - Document：`9482da85-13fc-4a30-a304-f8d8fb29e16f`
  - Part (lifecycle)：`8fce5908-9477-4e24-8f0c-8305ee6d9ba0`
  - CAD File (S5-A)：`9a7dad67-2ac2-46f1-bbb7-b3119f48c533`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 25  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```


## Run BC-5（BOM Compare：字段级对照复验）

- 时间：`2025-12-23 11:11:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`c249c7d0-74f1-49b9-992c-b2faa93c271f`
  - Parent B：`1882f18a-ebd9-4283-875f-f11794beca00`
  - Child X：`bfe0b639-3065-40ee-a978-2be6a55d07b2`
  - Child Y：`2de41ca2-ae54-41e9-ada1-2e3174668c6c`
  - Child Z：`3e08119d-2165-4735-b199-5bd553bde110`
  - Substitute：`082afa3b-4c6a-4968-96db-d6aacb3c3a34`

执行命令：

```bash
bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
ALL CHECKS PASSED
```


## Run S5-B-6（CAD 2D Connectors：auto-detect by content + CN keys）

- 时间：`2025-12-23 14:12:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`e2f659b9-59d2-44b8-a1d3-54497bcc169f`
  - ZWCAD File：`6904c7cf-b65b-4fba-a71e-10dba3c390cc`
  - Haochen File：`641ee1f9-bd21-4341-88a3-3bbb2194e57a`
  - Zhongwang File：`08df1968-5d40-40e0-881c-66b3ef463227`
  - Auto-detect File：`55bae091-624b-4ea7-88f5-cb93f14e151c`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```


## Run S5-C-4（CAD Attribute Sync：cad_extract + attributes endpoint，S3）

- 时间：`2025-12-23 14:12:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`628a5f85-b8cd-45fb-9f2d-ffbf75e17d88`
  - File：`b1078ffb-fc5a-47ee-96e4-6d39c8717852`
  - Job：`cdc8a2f3-40b0-4d6f-aecc-48b067a10da7`

执行命令：

```bash
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Attribute Sync Verification Complete
ALL CHECKS PASSED
```


## Run S5-C-LOCAL-3（CAD Extract Local Verification，CN keys）

- 时间：`2025-12-23 14:12:00 +0800`
- 脚本：`scripts/verify_cad_extract_local.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - PY：`.venv/bin/python`
  - PYTHONPATH：`src`
  - DB：`/tmp/yuantus_cad_extract_local.db`
  - Storage：`/tmp/yuantus_cad_extract_storage`
- 备注：`cadquery not installed`（已提示，未影响 cad_extract）

执行命令：

```bash
bash scripts/verify_cad_extract_local.sh
```

输出（摘要）：

```text
CAD Extract Local Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-Config（CAD Connectors Config Reload）

- 时间：`2025-12-23 15:09:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_config.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Demo File：`abcb82e2-ac65-43e4-9bb7-8167a51b82b4`

执行命令：

```bash
bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Connectors Config Verification Complete
ALL CHECKS PASSED
```


## Run S5-C-Template（CAD Sync Template）

- 时间：`2025-12-23 15:09:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync_template.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：
  - Part: item_number/description 设为 CAD sync
  - item_number cad_key=part_number

执行命令：

```bash
bash scripts/verify_cad_sync_template.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Sync Template Verification Complete
ALL CHECKS PASSED
```


## Run S5-C-Extractor（CAD Extractor Stub）

- 时间：`2025-12-23 15:09:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_stub.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`c4bdee3c-5501-45ce-bccb-d22be2c0fc13`
  - Job：`05e2f7d3-05b3-4ac9-a4be-888680ef4fa8`

执行命令：

```bash
bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor Stub Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-SVC（CAD Extractor Microservice）

- 时间：`2025-12-23 20:49:52 +0800`
- 基地址：`http://127.0.0.1:8200`
- 结果：`ALL CHECKS PASSED`
- 说明：
  - 使用临时 DWG 文件提交 `/api/v1/extract`
  - 返回 `ok=true` 且包含基础属性

执行命令（摘要）：

```bash
cd services/cad-extractor
../../.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8200 &
curl -s -X POST http://127.0.0.1:8200/api/v1/extract \
  -F "file=@/tmp/sample.dwg" \
  -F "cad_format=DWG"
```

输出（摘要）：

```json
{"ok":true,"attributes":{"file_name":"cad-extractor-XXXXXX.dwg","file_ext":"dwg","file_size_bytes":4,"part_number":"tmpXXXXXX","cad_format":"DWG"},"warnings":[]}
```

## Run S5-C-Extractor-Service（CAD Extractor Service Script）

- 时间：`2025-12-23 21:02:49 +0800`
- 基地址：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_service.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_cad_extractor_service.sh http://127.0.0.1:8200
```

输出（摘要）：

```text
CAD Extractor Service Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External（CAD Extractor External）

- 时间：`2025-12-23 21:29:13 +0800`
- 基地址：`http://127.0.0.1:7910`
- 外部服务：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`8b2e5c7a-a271-4d75-b5e2-2a31dc8b9d70`
  - Job：`e53ab992-ee1a-4c03-8b0d-88e684c7f0f6`

执行命令：

```bash
export CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200
export CAD_EXTRACTOR_SAMPLE_FILE=/tmp/yuantus_ext_XXXXXX.dwg
export CAD_EXTRACTOR_EXPECT_KEY=part_number
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL=http://localhost:59000
export YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000
export YUANTUS_S3_BUCKET_NAME=yuantus
export YUANTUS_S3_ACCESS_KEY_ID=minioadmin
export YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-RealDWG-Parsed（真实 DWG + 文件名解析）

- 时间：`2025-12-23 22:46:04 +0800`
- 基地址：`http://127.0.0.1:7910`
- 外部服务：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 校验：`part_number` 按文件名前缀解析
- 样例文件与关键 ID：
  - `J2824002-06上封头组件v2.dwg` → `part_number=J2824002-06`
    - File：`40021aa5-b21a-43a3-a519-28fafaea879e`
    - Job：`155260d8-23c2-4c2c-ba67-bb6240d367ae`
  - `J2825002-09下轴承支架组件v2.dwg` → `part_number=J2825002-09`
    - File：`c8fb59d5-7c42-4cd2-822e-20d75be79abb`
    - Job：`0ef33975-8de6-4036-ace9-75c7d457b917`
  - `J0724006-01下锥体组件v3.dwg` → `part_number=J0724006-01`
    - File：`b8904af3-2f3a-4864-bb34-17521dbdf5d9`
    - Job：`c1bf07b4-2641-439c-90f1-c7f152d835b3`

执行命令（示例）：

```bash
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06'
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run ALL-39（一键回归脚本：verify_all.sh，含 CAD Extractor Service）

- 时间：`2025-12-23 21:41:17 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：`PASS=24 / FAIL=0 / SKIP=2`
- 说明：
  - `Audit Logs`：`SKIP`（audit_enabled=False）
  - `S7 (Multi-Tenancy)`：`SKIP`（tenancy_mode=single）

执行命令：

```bash
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh
```

输出（摘要）：

```text
PASS: 24  FAIL: 0  SKIP: 2
ALL TESTS PASSED
```

## Run ALL-40（一键回归脚本：verify_all.sh，启用审计 + 多租户）

- 时间：`2025-12-23 22:00:56 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`ALL TESTS PASSED`
- 汇总：`PASS=26 / FAIL=0 / SKIP=0`
- 说明：
  - `tenancy_mode=db-per-tenant-org`
  - `audit_enabled=true`

执行命令：

```bash
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh
```

输出（摘要）：

```text
PASS: 26  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run S5-C-Extractor-External-RealDWG（CAD Extractor External：真实 DWG 样例）

- 时间：`2025-12-23 22:28:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 外部服务：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 样例文件与关键 ID：
  - `J2824002-06上封头组件v2.dwg`
    - File：`40021aa5-b21a-43a3-a519-28fafaea879e`
    - Job：`59fb1bb7-cd07-4102-83cf-554f6452207f`
  - `J2825002-09下轴承支架组件v2.dwg`
    - File：`c8fb59d5-7c42-4cd2-822e-20d75be79abb`
    - Job：`4255b4df-e560-49e9-8fcd-1ab53f23ae5f`
  - `J0724006-01下锥体组件v3.dwg`
    - File：`b8904af3-2f3a-4864-bb34-17521dbdf5d9`
    - Job：`7e60cc36-75c7-41aa-a386-da4ef0b96650`

执行命令（示例）：

```bash
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-RealDWG-Parsed-2（真实 DWG + 迁移修复）

- 时间：`2025-12-23 23:00:08 +0800`
- 基地址：`http://127.0.0.1:7910`
- 外部服务：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 修复：tenant DB 缺列 `meta_files.cad_document_path` → 执行 `yuantus db upgrade`
- 校验：`part_number` 按文件名前缀解析
- 样例文件与关键 ID：
  - `J2824002-06上封头组件v2.dwg` → `part_number=J2824002-06`
    - File：`40021aa5-b21a-43a3-a519-28fafaea879e`
    - Job：`1d874746-a2b1-4dc7-91ca-b6deda145c51`
  - `J2825002-09下轴承支架组件v2.dwg` → `part_number=J2825002-09`
    - File：`c8fb59d5-7c42-4cd2-822e-20d75be79abb`
    - Job：`0d8c361f-e47f-4f27-9766-8ab61dc9b261`
  - `J0724006-01下锥体组件v3.dwg` → `part_number=J0724006-01`
    - File：`b8904af3-2f3a-4864-bb34-17521dbdf5d9`
    - Job：`9f37c277-9df8-4024-8b01-4a0812add97c`

执行命令（示例）：

```bash
YUANTUS_TENANCY_MODE='db-per-tenant-org' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE='s3' \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-RealDWG-Sync（真实 DWG + 属性同步）

- 时间：`2025-12-23 23:10:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- 外部服务：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：`item_number <- part_number`，`description` 默认映射
- 样例文件与关键 ID：
  - `J2824002-06上封头组件v2.dwg` → `part_number=J2824002-06`
    - Part：`ac005a45-af28-4e89-9ae5-29d6b688bac8`
    - File：`40021aa5-b21a-43a3-a519-28fafaea879e`
    - Job：`3b147165-4aca-428a-85b2-443200150ab0`
  - `J2825002-09下轴承支架组件v2.dwg` → `part_number=J2825002-09`
    - Part：`d6079242-54d0-4142-a2c1-d99c01ab0369`
    - File：`c8fb59d5-7c42-4cd2-822e-20d75be79abb`
    - Job：`616f5232-420a-4055-9e4d-c527568634dc`
  - `J0724006-01下锥体组件v3.dwg` → `part_number=J0724006-01`
    - Part：`fc9b73c0-a32f-49a8-a47f-0a21b11b6283`
    - File：`b8904af3-2f3a-4864-bb34-17521dbdf5d9`
    - Job：`a48a78a1-efbf-4838-8386-5aad1965a9d4`

执行命令（示例）：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'

export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

CAD_SYNC_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_SYNC_EXPECT_ITEM_NUMBER='J2824002-06' \
CAD_SYNC_EXPECT_DESCRIPTION='上封头组件' \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Attribute Sync Verification Complete
ALL CHECKS PASSED
```

## Run S7-Tenant-Provisioning

- 时间：`2025-12-24 14:58:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 结果：`ALL CHECKS PASSED`
- 新租户：`tenant-provision-1766559513`
- 新组织：`org-provision-1766559513`
- 新管理员：`admin-1766559513`

执行命令（示例）：

```bash
export YUANTUS_TENANCY_MODE='single'
export YUANTUS_DATABASE_URL_TEMPLATE=''
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Tenant Provisioning Verification Complete
ALL CHECKS PASSED
```

## Run S7-Quota-Enforcement

- 时间：`2025-12-24 14:58:08 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_quotas.sh`
- 结果：`ALL CHECKS PASSED`
- 模式：`enforce`

执行命令（示例）：

```bash
export YUANTUS_TENANCY_MODE='single'
export YUANTUS_DATABASE_URL_TEMPLATE=''
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S6-Search-ECO-1

- 时间：`2025-12-24 15:18:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_search_eco.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - ECO Product：`b3cf30e3-048b-4d0f-988f-4d7704467a67`
  - ECO：`32790871-fb32-44ca-991a-8e59fe30fcb6`

执行命令（示例）：

```bash
export TENANCY_MODE='single'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'

bash scripts/verify_search_eco.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Search ECO Verification Complete
ALL CHECKS PASSED
```

## Run BC-7（BOM Compare：db-per-tenant-org 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`735fda45-952f-479b-b246-bea32049266a`
  - Parent B：`3e9a9026-514a-472b-88a2-d79f6e222ce5`
  - Child X：`4a78a43c-bb77-4f5c-b90c-e0e2dc76e635`
  - Child Y：`ac234177-c7ad-4aea-9dc4-9183a5d08d87`
  - Child Z：`0eb19021-b1a7-4054-9d28-3e9d0bfc543b`
  - Substitute：`8be13c71-09e1-41ca-9ac2-5faea0269ea3`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
ALL CHECKS PASSED
```

## Run WU-2（Where-Used API：db-per-tenant-org 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_where_used.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Assembly：`c0a27d75-0603-411e-bca7-f22dac414730`
  - Sub-Assembly：`810e9aad-978a-47a9-937e-566d75bf66ef`
  - Component：`096fab58-a800-4dc1-bc88-7234b5f4eea5`
  - Assembly2：`86ab8993-1fa1-4772-a813-a564e0cdc261`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Where-Used API Verification Complete
ALL CHECKS PASSED
```

## Run VF-3（Version-File Binding 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_version_files.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`b676981e-3177-4ca6-8e75-5d5ad38a5ed2`
  - Version：`ce7b4b9e-9cac-4119-a0a8-3abdcef61249`
  - File：`21134895-7b3f-493d-b64e-9849cbf85f6d`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Version-File Binding Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-9（CAD 2D Connectors：Haochen/Zhongwang + auto-detect 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD：`a6ec3ae9-ac4e-4ada-9a1c-1210f88fcaed`
  - ZWCAD：`80e1b6e6-64f6-41f5-9052-dffa2c1ba58f`
  - Haochen：`381e33e2-7baf-4fa4-a391-57a5fb2f5c3c`
  - Zhongwang：`39b095aa-5e69-4274-9d88-27b5af7a5200`
  - Auto-Haochen：`3e7282c4-0aaf-4b7a-a03d-91faf37031b3`
  - Auto-ZWCAD：`e9e6d9d0-85d7-400c-b8fd-c57c1d1cadda`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-10（CAD 3D Connectors：SolidWorks/NX/Creo/CATIA/Inventor 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_3d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - SolidWorks Part：`efb35c64-8f2c-4fc1-8a49-2e53566512b6`
  - SolidWorks ASM：`07750f52-5fff-4215-b438-a6e23a5b8a93`
  - NX：`f335757d-bc2f-428f-9cf8-968bd9d9e451`
  - Creo：`edfa01fd-1225-4429-9774-e7bf509af838`
  - CATIA：`fc62ae16-7764-4bb7-80cc-94659efbc298`
  - Inventor：`b698a28e-fb03-45ac-bd37-08be3a8b3f8b`
  - Auto-NX：`c5dba21b-04c3-407e-88dc-34803c95f083`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_cad_connectors_3d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 3D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-Config-3（CAD Connectors Config Reload 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_config.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Demo CAD File：`3809b563-91d1-4c10-893b-e412eedb9d89`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Connectors Config Verification Complete
ALL CHECKS PASSED
```

## Run MT-5（S7 多租户隔离：db-per-tenant-org 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export MODE='db-per-tenant-org'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
Multi-Tenancy Verification Complete
ALL CHECKS PASSED
```

## Run AUDIT-3（Audit Logs：db-per-tenant-org 复验）

- 时间：`2025-12-26 08:41:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_audit_logs.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Audit Logs Verification Complete
ALL CHECKS PASSED
```

## Run BC-8（BOM Compare：compare_mode 复验）

- 时间：`2025-12-26 08:57:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`3646e3f0-34e4-4ba3-b097-c6d4a3f26dea`
  - Parent B：`e252ad1b-2e81-4777-8386-7752e52c797a`
  - Child X：`85041e54-71e9-4cdd-8bd1-86c4e4bce6d8`
  - Child Y：`9f734f96-f4f7-48a5-ab67-6bdbdbbc9c6a`
  - Child Z：`2ea70974-8790-4273-99cc-49b78eafd3ea`
  - Substitute：`be5a2039-e5e5-4807-8b46-bd95d6b16e83`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
BOM Compare only_product: OK
BOM Compare num_qty: OK
ALL CHECKS PASSED
```

## Run S4-8（ECO Advanced：compare_mode 复验）

- 时间：`2025-12-26 09:03:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_eco_advanced.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Stage：`06e0664d-6de4-4fa8-a477-7b0036b40546`
  - Product：`29519d4e-e839-4326-a04f-8b4577863d06`
  - Assembly：`da4584df-c59a-4116-84dc-e14e75b29848`
  - ECO1：`add60ef9-6299-4fc3-bb04-24878d954890`
  - Target Version：`24b18abc-6cf3-4485-b6f4-be20622222f6`
  - ECO2：`a1b139d2-3775-43d3-b43b-04490af72e35`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM diff: OK
BOM diff only_product: OK
Impact analysis: OK
Impact export files: OK
Batch approvals (admin): OK
Batch approvals (viewer denied): OK
ALL CHECKS PASSED
```

## Run S5-C-Normalization-1（CAD Attribute Normalization）

- 时间：`2025-12-26 08:23:22 +0800`
- 脚本：`scripts/verify_cad_attribute_normalization.sh`
- 结果：`ALL CHECKS PASSED`
- 关键校验：
  - `material=Stainless Steel 304`
  - `weight=1.2`（1200g → 1.2kg）
  - `revision=A`（REV-A → A）
  - `drawing_no` 补齐

执行命令：

```bash
bash scripts/verify_cad_attribute_normalization.sh
```

输出（摘要）：

```text
CAD Attribute Normalization Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-Connectors-2D-2（Auto Detect ZWCAD）

- 时间：`2025-12-26 08:23:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Auto ZWCAD File：`2faf98da-517d-43f4-a892-f9ecf955c00f`
  - Auto Haochen File：`7af13c80-2d87-4553-a7fb-bcfdc5d28bfb`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run S7-Tenant-Provisioning-2（Platform Admin Enabled）

- 时间：`2025-12-26 00:31:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Tenant：`tenant-provision-1766680281`
  - Default Org：`org-provision-1766680281`
  - Extra Org：`org-extra-1766680281`
  - Admin：`admin-1766680281`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Tenant Provisioning Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-17（DWG：J2825002-09）

- 时间：`2025-12-26 00:35:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 样例：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg`
- 关键 ID：
  - File：`b3de1296-953e-492a-b724-13f53133d5de`
  - Job：`f7e181bb-3537-4fb5-968a-f2969c680402`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg'
export CAD_EXTRACTOR_CAD_FORMAT='AUTOCAD'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-18（DWG：J0724006-01）

- 时间：`2025-12-26 00:35:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 样例：`/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg`
- 关键 ID：
  - File：`bd95109c-ac7f-4fa4-8919-1dcb0f7e01ce`
  - Job：`1f5a5e85-6b9c-4f08-a602-e3ed23f42d16`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg'
export CAD_EXTRACTOR_CAD_FORMAT='AUTOCAD'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-19（STEP：CNC）

- 时间：`2025-12-26 00:35:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 样例：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
- 关键 ID：
  - File：`a2bc42b4-2057-43b9-bfbd-fd98b7e37c07`
  - Job：`aae7618f-924e-4160-9059-f4f803929026`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp'
export CAD_EXTRACTOR_CAD_FORMAT='STEP'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-20（PRT：model2）

- 时间：`2025-12-26 00:35:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 样例：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`
- 关键 ID：
  - File：`40894817-c7ef-49ac-a59d-bca77e8bb090`
  - Job：`b406a20d-982a-4579-a1d6-7845a484e2e8`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt'
export CAD_EXTRACTOR_CAD_FORMAT='NX'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-Coverage-Refresh-1（覆盖率刷新）

- 时间：`2025-12-26 00:34:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 结果：`覆盖率报告已更新`
- 覆盖率亮点：
  - Training DWG：`drawing_no` 100%
  - JCB1：`revision`/`drawing_no` 100%
  - UG：`drawing_no` 75%
  - Ling-jian PRT：`drawing_no` 100%

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CLI='.venv/bin/yuantus'

PY=.venv/bin/python
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format AUTOCAD --dir "/Users/huazhou/Downloads/训练图纸/训练图纸" --extensions dwg --output docs/CAD_EXTRACTOR_COVERAGE_TRAINING_DWG.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format NX --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug" --output docs/CAD_EXTRACTOR_COVERAGE_UG.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format CREO --dir "/Users/huazhou/Downloads/JCB1" --output docs/CAD_EXTRACTOR_COVERAGE_JCB1.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format CATIA --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions catpart,catproduct --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_CATIA.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format STEP --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions step,stp --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_STEP.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format IGES --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions iges,igs --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_IGES.md
$PY scripts/collect_cad_extractor_coverage.py --base-url http://127.0.0.1:7910 --tenant tenant-1 --org org-1 --cad-format NX --dir "/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian" --extensions prt,asm --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_PRT.md
```

输出（摘要）：

```text
Coverage reports updated
```

## Run S5-A-Preview-2D-1

- 时间：`2025-12-25 23:55:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`
  - Preview HTTP：`302`

执行命令：

```bash
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
OK: Preview endpoint HTTP 302
ALL CHECKS PASSED
```

## Run S5-C-OCR-TitleBlock-3（CAD OCR Title Block）

- 时间：`2025-12-25 23:59:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_ocr_titleblock.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`69046186-de6b-498d-93ea-efa40431d169`
  - OCR Keys：`drawing_no`

执行命令：

```bash
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_AUTH_MODE=required

bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
OK: Extracted OCR attributes: drawing_no
ALL CHECKS PASSED
```

## Run S5-C-Filename-Parse-1（CAD Filename Parsing）

- 时间：`2025-12-26 00:09:29 +0800`
- 脚本：`scripts/verify_cad_filename_parse.sh`
- 结果：`ALL CHECKS PASSED`
- 覆盖样例：
  - `model2.prt.1` → revision=`1`
  - `J2824002-06上封头组件v2.dwg` → part_number=`J2824002-06`
  - `比较_J2825002-09下轴承支架组件v2.dwg` → part_number=`J2825002-09`

执行命令：

```bash
bash scripts/verify_cad_filename_parse.sh
```

输出（摘要）：

```text
CAD Filename Parsing Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-LocalExtract-2（CAD Extract Local）

- 时间：`2025-12-26 00:11:02 +0800`
- 脚本：`scripts/verify_cad_extract_local.sh`
- 结果：`ALL CHECKS PASSED`
- 关键校验：
  - `part_number=HC-LOCAL-001`
  - `weight=1.2`（解析自 `1.2kg`）

执行命令：

```bash
bash scripts/verify_cad_extract_local.sh
```

输出（摘要）：

```text
CAD Extract Local Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-Coverage-UG（NX 字段覆盖率统计）

- 时间：`2025-12-25 22:16:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug`
- 结果：`4 files`
- 覆盖率摘要：
  - `part_number`: 4/4
  - `part_name`: 0/4
  - `material`: 0/4
  - `weight`: 0/4
  - `revision`: 0/4
  - `drawing_no`: 0/4
  - `author`: 0/4
  - `created_at`: 0/4
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_UG.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format NX \
    --dir /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug \
    --output docs/CAD_EXTRACTOR_COVERAGE_UG.md
```

## Run S5-C-Extractor-Coverage-JCB1（Creo 字段覆盖率统计）

- 时间：`2025-12-25 16:04:51 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/JCB1`
- 结果：`16 files`
- 覆盖率摘要：
  - `part_number`: 16/16
  - `part_name`: 0/16
  - `material`: 0/16
  - `weight`: 0/16
  - `revision`: 0/16
  - `drawing_no`: 0/16
  - `author`: 0/16
  - `created_at`: 0/16
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_JCB1.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format CREO \
    --dir /Users/huazhou/Downloads/JCB1 \
    --output docs/CAD_EXTRACTOR_COVERAGE_JCB1.md
```

## Run S5-C-Extractor-Coverage-LingJian-CATIA（CATIA 字段覆盖率统计）

- 时间：`2025-12-25 22:23:57 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- 结果：`6 files`
- 覆盖率摘要：
  - `part_number`: 6/6
  - `part_name`: 0/6
  - `material`: 0/6
  - `weight`: 0/6
  - `revision`: 0/6
  - `drawing_no`: 0/6
  - `author`: 0/6
  - `created_at`: 0/6
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_CATIA.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format CATIA \
    --extensions catpart \
    --dir /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian \
    --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_CATIA.md
```

## Run S5-C-Extractor-Coverage-LingJian-STEP（STEP 字段覆盖率统计）

- 时间：`2025-12-25 22:24:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- 结果：`1 files`
- 覆盖率摘要：
  - `part_number`: 1/1
  - `part_name`: 0/1
  - `material`: 0/1
  - `weight`: 0/1
  - `revision`: 0/1
  - `drawing_no`: 0/1
  - `author`: 0/1
  - `created_at`: 0/1
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_STEP.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format STEP \
    --extensions stp \
    --dir /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian \
    --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_STEP.md
```

## Run S5-C-Extractor-Coverage-LingJian-IGES（IGES 字段覆盖率统计）

- 时间：`2025-12-25 22:24:21 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- 结果：`1 files`
- 覆盖率摘要：
  - `part_number`: 1/1
  - `part_name`: 0/1
  - `material`: 0/1
  - `weight`: 0/1
  - `revision`: 0/1
  - `drawing_no`: 0/1
  - `author`: 0/1
  - `created_at`: 0/1
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_IGES.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format IGES \
    --extensions igs \
    --dir /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian \
    --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_IGES.md
```

## Run S5-C-Extractor-Coverage-LingJian-PRT（PRT 字段覆盖率统计）

- 时间：`2025-12-25 22:34:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian`
- 结果：`6 files`
- 覆盖率摘要：
  - `part_number`: 6/6
  - `part_name`: 0/6
  - `material`: 0/6
  - `weight`: 0/6
  - `revision`: 0/6
  - `drawing_no`: 0/6
  - `author`: 0/6
  - `created_at`: 0/6
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_PRT.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format NX \
    --extensions prt \
    --dir /Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian \
    --output docs/CAD_EXTRACTOR_COVERAGE_LINGJIAN_PRT.md
```

## Run S5-C-Extractor-Coverage-Training-DWG（训练图纸 DWG 字段覆盖率统计）

- 时间：`2025-12-25 22:49:29 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 目录：`/Users/huazhou/Downloads/训练图纸/训练图纸`
- 结果：`110 files`
- 覆盖率摘要：
  - `part_number`: 110/110
  - `part_name`: 110/110
  - `material`: 0/110
  - `weight`: 0/110
  - `revision`: 109/110
  - `drawing_no`: 0/110
  - `author`: 0/110
  - `created_at`: 0/110
- 报告：`docs/CAD_EXTRACTOR_COVERAGE_TRAINING_DWG.md`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
  .venv/bin/python scripts/collect_cad_extractor_coverage.py \
    --base-url http://127.0.0.1:7910 \
    --tenant tenant-1 \
    --org org-1 \
    --cad-format AUTOCAD \
    --extensions dwg \
    --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
    --output docs/CAD_EXTRACTOR_COVERAGE_TRAINING_DWG.md
```

## Run S5-C-Extractor-External-15（CAD Extractor External：Creo PRT 版本号文件）

- 时间：`2025-12-25 15:36:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/JCB1/prt0098.prt.26`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`0b5bb490-3740-4655-ae94-9067a99b663e`
  - Job：`1b41a0d1-3810-47a3-ae29-3b403a3db97e`
- 校验：`part_number=prt0098.prt`，`cad_format=CREO`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/JCB1/prt0098.prt.26' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='prt0098.prt' \
CAD_EXTRACTOR_CAD_FORMAT='CREO' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run S5-C-OCR-TitleBlock-1（CAD OCR Title Block）

- 时间：`2025-12-25 23:08:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_ocr_titleblock.sh`
- 结果：`SKIP`
- 原因：`CAD ML Vision not available at http://localhost:8001/api/v1/vision/health`

执行命令：

```bash
bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run S5-C-OCR-TitleBlock-2（CAD OCR Title Block）

- 时间：`2025-12-25 23:48:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- CAD ML：`http://127.0.0.1:8001`
- 脚本：`scripts/verify_cad_ocr_titleblock.sh`
- 结果：`ALL CHECKS PASSED`
- 提取字段：`drawing_no`

执行命令：

```bash
export YUANTUS_CAD_ML_BASE_URL='http://127.0.0.1:8001'
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-16（CAD Extractor External：Creo ASM 版本号文件）

- 时间：`2025-12-25 15:36:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/JCB1/asm0010.asm.18`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`2a9abc28-cc49-400e-a194-ed25cc0b1bea`
  - Job：`089bfeff-216a-43b3-96e3-ebd0b253d4c2`
- 校验：`part_number=asm0010.asm`，`cad_format=CREO`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/JCB1/asm0010.asm.18' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='asm0010.asm' \
CAD_EXTRACTOR_CAD_FORMAT='CREO' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-11（CAD Extractor External：NX/UG 样例 peihejian）

- 时间：`2025-12-25 13:18:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/peihejian.prt`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`1dfbd48e-0496-452f-b38f-60b3c762886e`
  - Job：`0c940dcc-b2bd-4329-9bec-6694dff67f25`
- 校验：`part_number=peihejian`，`cad_format=NX`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/peihejian.prt' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='peihejian' \
CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-12（CAD Extractor External：NX/UG 样例 jian2）

- 时间：`2025-12-25 13:18:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/jian2.prt`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`996d865f-3282-434e-b9a4-05cb57187791`
  - Job：`bd5f8d93-94d1-47e4-bd05-dfa7a9cd9c9a`
- 校验：`part_number=jian2`，`cad_format=NX`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/jian2.prt' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='jian2' \
CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-13（CAD Extractor External：NX/UG 样例 jian3）

- 时间：`2025-12-25 13:18:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/jian3.prt`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`d30f41b8-1430-4021-9c73-d3312bf3ae92`
  - Job：`79bafcca-47cb-410f-b61f-7e81a20e97a1`
- 校验：`part_number=jian3`，`cad_format=NX`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/jian3.prt' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='jian3' \
CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-14（CAD Extractor External：NX/UG 样例 jian1）

- 时间：`2025-12-25 13:18:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/jian1.prt`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`a3c9432c-d10e-4fda-a81f-675d6a9fd0e1`
  - Job：`8dc84249-ce50-47c0-89ef-d5ccc08bc6b3`
- 校验：`part_number=jian1`，`cad_format=NX`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/比较杂的收藏/ug/jian1.prt' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='jian1' \
CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-7（CAD Extractor External：CATIA 样例）

- 时间：`2025-12-25 11:41:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/Part1.CATPart`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`df6d6c62-bd2d-4b02-b3aa-3681b556f2c0`
  - Job：`35f7596b-f5e7-4cc1-8f30-68f9093fc997`
- 校验：`part_number=Part1`，`cad_format=CATIA`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/Part1.CATPart' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='Part1' \
CAD_EXTRACTOR_CAD_FORMAT='CATIA' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-8（CAD Extractor External：STEP 样例）

- 时间：`2025-12-25 11:41:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/pat4.stp`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`dcc2fbfe-ed64-46f0-a0cb-3c88f0679a81`
  - Job：`3ee10fc5-0eb7-4e4f-aa26-65d4182cc23e`
- 校验：`part_number=pat4`，`cad_format=STEP`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/pat4.stp' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='pat4' \
CAD_EXTRACTOR_CAD_FORMAT='STEP' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-9（CAD Extractor External：NX PRT 样例）

- 时间：`2025-12-25 11:41:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/Part1_catpart.prt`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`6ba291bb-5b0b-4a6d-92fe-3a7fd9e4b386`
  - Job：`c8b0a2db-b273-4ba4-8ce6-f2a39cc30ad7`
- 校验：`part_number=Part1_catpart`，`cad_format=NX`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/Part1_catpart.prt' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='Part1_catpart' \
CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-10（CAD Extractor External：IGES 样例）

- 时间：`2025-12-25 11:41:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/FrontCarframe_zyl.igs`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`13a1db25-d530-4842-9961-b8df0040e6ac`
  - Job：`d9fa9d58-48cc-4f1d-89cd-e3b67ce181c5`
- 校验：`part_number=FrontCarframe_zyl`，`cad_format=IGES`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/复杂产品出图/ling-jian/FrontCarframe_zyl.igs' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='FrontCarframe_zyl' \
CAD_EXTRACTOR_CAD_FORMAT='IGES' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-5（CAD Extractor External：STEP 样例）

- 时间：`2025-12-24 17:29:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`a2bc42b4-2057-43b9-bfbd-fd98b7e37c07`
  - Job：`2afa1880-f860-4780-9055-32ed6c9f37a4`
- 校验：`part_number=CNC`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='CNC' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-6（CAD Extractor External：NX PRT 样例）

- 时间：`2025-12-24 17:30:38 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 样例文件：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`40894817-c7ef-49ac-a59d-bca77e8bb090`
  - Job：`186b87a1-2dce-4793-91ec-7aa96523facf`
- 校验：`part_number=model2`，`cad_format=NX`（覆盖）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME='yuantus' \
S3_ACCESS_KEY_ID='minioadmin' \
S3_SECRET_ACCESS_KEY='minioadmin' \
CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='model2' \
CAD_EXTRACTOR_CAD_FORMAT='NX' \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-8（CAD 3D Connectors：SolidWorks/NX/Creo/CATIA/Inventor）

- 时间：`2025-12-24 17:21:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_3d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - SolidWorks Part：`a30ff1f5-5799-42ee-936d-c1a7e2736119`
  - SolidWorks Assembly：`b589f349-b7d5-4635-ad52-aa22fc6a324c`
  - NX：`e44d0435-0fb0-4c0f-a538-3577dd7c3a06`
  - Creo：`7b16cca9-50a0-49c8-8bb1-76f4647cc471`
  - CATIA：`8dfe6cbb-3922-4603-89c3-62d7253b6a06`
  - Inventor：`948b8311-d9da-477c-af41-59c69aa7a30a`
  - Auto (NX default)：`aac23326-091b-4e2b-9c3a-01021a0dc668`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_cad_connectors_3d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 3D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run ALL-49（一键回归：verify_all.sh，全量 + S3 + 多租户 + 配额 + CAD Extractor）

- 时间：`2025-12-24 16:51:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- Tenancy：`db-per-tenant-org`
- 结果：`PASS=34, FAIL=0, SKIP=0`
- 说明：启用 `S5-C` Auto Part/Extractor Stub/External/Service + `S7 Tenant Provisioning` + `Quota enforce`，并使用 S3 存储模式

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_PLATFORM_ADMIN_ENABLED='true'
export YUANTUS_QUOTA_MODE='enforce'
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=1
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06'

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 34  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run ALL-41（一键回归脚本：verify_all.sh，db-per-tenant-org + S3 + quota enforce）

- 时间：`2025-12-24 16:43:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 29 / FAIL 0 / SKIP 5`
- 模式：`db-per-tenant-org`
- 审计：`enabled`
- 配额：`enforce`
- 跳过项：
  - `S5-C (CAD Auto Part)`：`RUN_CAD_AUTO_PART=0`
  - `S5-C (CAD Extractor Stub)`：`RUN_CAD_EXTRACTOR_STUB=0`
  - `S5-C (CAD Extractor External)`：`RUN_CAD_EXTRACTOR_EXTERNAL=0`
  - `S5-C (CAD Extractor Service)`：`RUN_CAD_EXTRACTOR_SERVICE=0`
  - `S7 (Tenant Provisioning)`：`RUN_TENANT_PROVISIONING=0`
- 关键 ID（节选）：
  - Run H Part：`5b6b199a-0bb0-4657-a3c7-e353ad079ba7`
  - Run H RPC Part：`cb01fa5a-1315-4729-9cb9-6e9dac8cf580`
  - Run H File：`f37106f7-75b4-482f-8c29-99f3cb872f96`
  - Run H ECO：`a30f728d-3634-44cf-87b9-f44c3d7098d0`
  - S5-A File：`6520876b-cd7e-4132-9cdf-df47f9bcf3af`
  - S5-B GStarCAD File：`1fe3e4af-a6ad-4cee-9403-a240a08fc828`
  - S5-C Item：`29279aab-4ac4-4cc2-afd4-a3cf7ef4d433`
  - Search Index Part：`edb3b613-f4f1-4f1c-885f-d7a0ec3b0192`
  - Search ECO：`8c5e23fc-03de-4db8-b015-effb1894dd4e`
  - Reports Summary Part：`b6acb6a2-6dfe-42e4-8b82-f852ad2713f9`
  - BOM Compare Parent A：`beb38b70-0c96-436d-921c-8b43092c0fdd`
  - Baseline：`d10e42d5-bb6b-4b84-a5e9-c1c93ffe4fc9`
  - MBOM Root：`92a16c1b-3c42-4ec2-9d8b-f2821f8cf548`
  - Version-File Binding Part：`2bb705c1-d0b0-4a5e-b4e0-1f354f1d6224`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE='s3' \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_BUCKET_NAME='yuantus' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
YUANTUS_PLATFORM_ADMIN_ENABLED=true \
YUANTUS_QUOTA_MODE=enforce \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 29  FAIL: 0  SKIP: 5
ALL TESTS PASSED
```

## Run S5-B-7（CAD 2D Connectors：Haochen/Zhongwang + auto-detect）

- 时间：`2025-12-24 16:29:50 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD File：`e540edb1-dc39-4bd3-9c61-c976513d3899`
  - ZWCAD File：`4ef8a839-45e3-44eb-a318-a4b74ef728d4`
  - Haochen File：`cf998a0f-0f4c-4e8a-8946-c49241e59159`
  - Zhongwang File：`2c9dba7b-4cf7-4c09-8fae-fdb0f94d85d4`
  - Auto-detect File：`c833e090-27a9-4c11-80c6-0703c2a591f1`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'

bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD 2D Connectors Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-Service-2（CAD Extractor Service）

- 时间：`2025-12-24 16:30:15 +0800`
- 基地址：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_service.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_cad_extractor_service.sh
```

输出（摘要）：

```text
CAD Extractor Service Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-5（CAD Attribute Sync，S3）

- 时间：`2025-12-24 16:31:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`e48276d5-4a0c-414b-a748-b2d589dfbb0e`
  - File：`33ba8986-0f6c-4278-930c-1e19abfa2e12`
  - Job：`8cb29ec1-c16d-49f8-bb64-0e6aa8f66a43`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'

bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Attribute Sync Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-2（CAD Extractor External）

- 时间：`2025-12-24 16:31:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`
  - Job：`6cdc1dda-dbec-4c51-b591-f1175f848653`
- 样例文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
- 校验字段：`part_number=J2824002-06`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06'

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-3（CAD Extractor External）

- 时间：`2025-12-24 16:41:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`b3de1296-953e-492a-b724-13f53133d5de`
  - Job：`dca02896-eb88-4cfb-ba12-2cb743dcae9b`
- 样例文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg`
- 校验字段：`part_number=J2825002-09`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='J2825002-09'

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Extractor-External-4（CAD Extractor External）

- 时间：`2025-12-24 16:41:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`bd95109c-ac7f-4fa4-8919-1dcb0f7e01ce`
  - Job：`154da872-3087-43eb-9e1e-4371437a6c28`
- 样例文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg`
- 校验字段：`part_number=J0724006-01`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='J0724006-01'

bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Extractor External Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-Config-2（CAD Connectors Config Reload）

- 时间：`2025-12-24 16:32:20 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_config.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Demo File：`3809b563-91d1-4c10-893b-e412eedb9d89`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Connectors Config Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Template-2（CAD Sync Template）

- 时间：`2025-12-24 16:32:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync_template.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_cad_sync_template.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Sync Template Verification Complete
ALL CHECKS PASSED
```

## Run S5-C-Auto-Part-2（CAD Auto Part）

- 时间：`2025-12-24 16:32:42 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_auto_part.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`3d83bd23-396d-4b29-b5be-98c3c964cc1c`
  - File：`13fe63b3-a315-41aa-9c4b-3c3d5db1d0a9`
  - Attachment：`9d6cd39e-df9f-4158-924c-b267fc46ec80`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_BUCKET_NAME='yuantus'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'

bash scripts/verify_cad_auto_part.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Auto Part Verification Complete
ALL CHECKS PASSED
```

## Run S7-MT-3（Multi-Tenancy：db-per-tenant-org，Docker 7910）

- 时间：`2025-12-24 16:17:56 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 模式：`db-per-tenant-org`
- 关键 ID：无（脚本未输出）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
Multi-Tenancy Verification Complete
ALL CHECKS PASSED
```

## Run S7-Q-4（Quota enforce / Docker 7910）

- 时间：`2025-12-24 16:18:03 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_quotas.sh`
- 结果：`ALL CHECKS PASSED`
- 模式：`enforce`（YUANTUS_QUOTA_MODE）

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-TP-2（Tenant Provisioning）

- 时间：`2025-12-24 16:16:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 结果：`ALL CHECKS PASSED`
- 平台开关：`enabled`（YUANTUS_PLATFORM_ADMIN_ENABLED=true）
- 关键 ID：
  - Tenant：`tenant-provision-1766564172`
  - Default Org：`org-provision-1766564172`
  - Extra Org：`org-extra-1766564172`
  - Admin：`admin-1766564172`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_PLATFORM_ADMIN_ENABLED=true \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Tenant Provisioning Verification Complete
ALL CHECKS PASSED
```

## Run BK-6（Backup/Restore 验证）

- 时间：`2025-12-24 16:16:28 +0800`
- 项目：`yuantus`
- 脚本：`scripts/verify_backup_restore.sh`
- 结果：`ALL CHECKS PASSED`
- 关键路径：
  - BACKUP_DIR：`/tmp/yuantus_backup_verify_1766564188`
  - RESTORE_DB_SUFFIX：`_restore_1766564188`
  - RESTORE_DB：`yuantus_restore_1766564188`
  - RESTORE_BUCKET：`yuantus-restore-test-1766564188`

执行命令：

```bash
PROJECT=yuantus bash scripts/verify_backup_restore.sh
```

输出（摘要）：

```text
Backup/Restore Verification Complete
ALL CHECKS PASSED
```

## Run BK-7（Backup Rotation 验证）

- 时间：`2025-12-24 16:18:23 +0800`
- 脚本：`scripts/verify_backup_rotation.sh`
- 结果：`ALL CHECKS PASSED`
- BACKUP_ROOT：`/tmp/yuantus_backup_rotate_test`
- KEEP：`2`（保留 `yuantus_003`, `yuantus_002`）

执行命令：

```bash
bash scripts/verify_backup_rotation.sh
```

输出（摘要）：

```text
Rotation complete.
ALL CHECKS PASSED
```

## Run BC-6（BOM Compare：db-per-tenant-org 复验）

- 时间：`2025-12-24 16:03:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent A：`d1295b0c-1146-4375-bcae-579bdf80a77c`
  - Parent B：`8dd20e04-7d12-4d2b-bf23-4b5c84a22e1e`
  - Child X：`ee5eb378-8c50-45d8-920a-f6bc18e3f347`
  - Child Y：`acedd41e-1062-40a6-85f6-e9cfebefd920`
  - Child Z：`793e003f-0a7a-484a-bf95-dd31c03cf90a`
  - Substitute：`4485b9c1-aed7-4ffe-a8e6-6c46e98e7b1f`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Compare: OK
ALL CHECKS PASSED
```

## Run SUB-2（BOM Substitutes：db-per-tenant-org 复验）

- 时间：`2025-12-24 16:03:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_substitutes.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent：`9e38cad0-5692-44a2-9385-ff598257e65e`
  - Child：`693a5505-1aec-4179-a3be-a93178b53e64`
  - BOM Line：`63d01422-e75e-47df-af04-1e9607e58323`
  - Substitute 1：`4ecd6cc9-3fcc-4640-b683-bf0e981aeb53`
  - Substitute 2：`45009196-5d87-42a8-a4e9-557896054836`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_substitutes.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
BOM Substitutes Verification Complete
ALL CHECKS PASSED
```

## Run S4-7（ECO Advanced：Batch approvals 修复后复验）

- 时间：`2025-12-24 16:05:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_eco_advanced.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Stage：`c8832912-9915-43f0-a0b6-2d15cf4c9575`
  - Product：`7b5704d2-35d4-43da-b6c0-15e4c1a34be5`
  - Assembly：`4a0844f9-73b9-4f2f-8786-2f620920a7ef`
  - ECO1：`62c0f1fc-c05b-467d-ad2c-9960f0be94e9`
  - ECO2：`2f0efac9-bb31-4d1c-b56a-abdd3a554cdb`
  - Target Version：`6f8fe54d-ba21-4a04-b478-f35ac0e1df7c`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ECO Advanced Verification Complete
ALL CHECKS PASSED
```

## Run S6-Search-ECO-2

- 时间：`2025-12-24 15:40:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_search_eco.sh`
- 结果：`ALL CHECKS PASSED`
- 引擎：`db`
- 关键 ID：
  - ECO Product：`03177cbe-e560-4709-88cd-283613c4b11f`
  - ECO：`946fe6a1-5889-44f2-bb7a-e18826f3fc32`

执行命令（示例）：

```bash
export TENANCY_MODE='single'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'

bash scripts/verify_search_eco.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Search ECO Verification Complete
ALL CHECKS PASSED
```

## Run ALL-50（一键回归：verify_all.sh，端口修正 55432）

- 时间：`2025-12-26 09:27:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 34 / FAIL 0 / SKIP 5`
- 说明：修正 Postgres 端口（5434 → 55432）后全量回归通过。

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export RUN_CAD_AUTO_PART=0
export RUN_CAD_EXTRACTOR_STUB=0
export RUN_CAD_EXTRACTOR_EXTERNAL=0
export RUN_CAD_EXTRACTOR_SERVICE=0
export RUN_TENANT_PROVISIONING=0

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 34  FAIL: 0  SKIP: 5
ALL TESTS PASSED
```

## Run ALL-51（一键回归：verify_all.sh，全量 + CAD Extractor External）

- 时间：`2025-12-26 09:40:24 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 38 / FAIL 0 / SKIP 1`
- 说明：包含 CAD Auto Part + CAD Extractor Stub/External/Service 全量验证。
- 关键输入：
  - CAD_EXTRACTOR_SAMPLE_FILE=`/tmp/EXT-123-External-v2.dwg`
  - CAD_EXTRACTOR_EXPECT_KEY=`part_number`
  - CAD_EXTRACTOR_EXPECT_VALUE=`EXT-123-External`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=0
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/tmp/EXT-123-External-v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='EXT-123-External'

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 38  FAIL: 0  SKIP: 1
ALL TESTS PASSED
```

## Run TP-1（Tenant Provisioning：platform admin 启用）

- 时间：`2025-12-26 09:47:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - NEW_TENANT：`tenant-provision-1766713630`
  - NEW_ORG：`org-provision-1766713630`
  - EXTRA_ORG：`org-extra-1766713630`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
export YUANTUS_PLATFORM_TENANT_ID=platform
export YUANTUS_PLATFORM_ORG_ID=platform

bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Tenant Provisioning Verification Complete
ALL CHECKS PASSED
```

## Run ALL-52（一键回归：verify_all.sh，全量 + Tenant Provisioning）

- 时间：`2025-12-26 09:50:07 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 39 / FAIL 0 / SKIP 0`
- 说明：平台管理员开启，包含 Tenant Provisioning、CAD Auto Part、CAD Extractor（stub/external/service）全量验证。

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
export YUANTUS_PLATFORM_TENANT_ID=platform
export YUANTUS_PLATFORM_ORG_ID=platform
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=1
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/tmp/EXT-123-External-v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='EXT-123-External'

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 39  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run CAD-REAL-1（真实 CAD 样本：DWG/STEP/PRT）

- 时间：`2025-12-26 10:11:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_real_samples.sh`
- 结果：`ALL CHECKS PASSED`
- 样本：
  - DWG：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
  - STEP：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
  - PRT：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`
- 关键 ID：
  - DWG：file_id=`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`, item_id=`cc4809a5-6ad5-419d-b9f1-8e6bb7582e09`
  - STEP：file_id=`a2bc42b4-2057-43b9-bfbd-fd98b7e37c07`, item_id=`cdaffdde-9824-4232-b8fa-231f4fe24c81`
  - PRT：file_id=`40894817-c7ef-49ac-a59d-bca77e8bb090`, item_id=`b4fa56e2-a7a7-47ab-8dd6-9c21d9b9d01b`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_ML_BASE_URL='http://localhost:8001'

bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
CAD Real Samples Verification Complete
ALL CHECKS PASSED
```

## Run ALL-53（一键回归：verify_all.sh，全量 + CAD Real Samples）

- 时间：`2025-12-26 10:20:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 40 / FAIL 0 / SKIP 0`
- 说明：平台管理员开启，包含 Tenant Provisioning、CAD Auto Part、CAD Extractor（stub/external/service）、CAD Real Samples 全量验证。

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
export YUANTUS_PLATFORM_TENANT_ID=platform
export YUANTUS_PLATFORM_ORG_ID=platform
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_CAD_REAL_SAMPLES=1
export RUN_TENANT_PROVISIONING=1
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/tmp/EXT-123-External-v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='EXT-123-External'
export CAD_ML_BASE_URL='http://localhost:8001'

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full5.log
```

输出（摘要）：

```text
PASS: 40  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run CAD-REAL-2（真实 CAD 样本：DWG/STEP/PRT 复跑）

- 时间：`2025-12-26 13:04:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_real_samples.sh`
- 结果：`ALL CHECKS PASSED`
- 样本：
  - DWG：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
  - STEP：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
  - PRT：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`
- 关键 ID：
  - DWG：file_id=`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`, item_id=`cc4809a5-6ad5-419d-b9f1-8e6bb7582e09`
  - STEP：file_id=`a2bc42b4-2057-43b9-bfbd-fd98b7e37c07`, item_id=`cdaffdde-9824-4232-b8fa-231f4fe24c81`
  - PRT：file_id=`40894817-c7ef-49ac-a59d-bca77e8bb090`, item_id=`b4fa56e2-a7a7-47ab-8dd6-9c21d9b9d01b`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_ML_BASE_URL='http://localhost:8001'

bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_cad_real_samples_rerun.log
```

输出（摘要）：

```text
CAD Real Samples Verification Complete
ALL CHECKS PASSED
```

## Run ALL-54（一键回归：verify_all.sh，全量 + CAD Real Samples）

- 时间：`2025-12-26 13:07:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 40 / FAIL 0 / SKIP 0`
- 说明：平台管理员开启，包含 Tenant Provisioning、CAD Auto Part、CAD Extractor（stub/external/service）、CAD Real Samples 全量验证。

执行命令：

```bash
export RUN_CAD_REAL_SAMPLES=1
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
export YUANTUS_PLATFORM_TENANT_ID=platform
export YUANTUS_PLATFORM_ORG_ID=platform
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=1
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/tmp/EXT-123-External-v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='EXT-123-External'
export CAD_ML_BASE_URL='http://localhost:8001'

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full6.log
```

输出（摘要）：

```text
PASS: 40  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run S5-C-Normalization-2（CAD Attribute Normalization：Haochen/Zhongwang aliases）

- 时间：`2025-12-26 13:20:02 +0800`
- 脚本：`scripts/verify_cad_attribute_normalization.sh`
- 结果：`ALL CHECKS PASSED`
- 关键校验：
  - Haochen：`material=Stainless Steel 304`, `weight=1.2`, `revision=A`, `drawing_no` 补齐
  - Zhongwang：`drawing_no=ZW-002`, `material=Q235 Steel`, `revision=B`, `weight=2.5`
  - 别名：`图纸编号/图纸名称/版次/材质/重量(kg)`

执行命令：

```bash
bash scripts/verify_cad_attribute_normalization.sh
```

输出（摘要）：

```text
CAD Attribute Normalization Verification Complete
ALL CHECKS PASSED
```

## Run S5-B-Real-2D-1（真实样本 2D 连接器：Haochen/Zhongwang）

- 时间：`2025-12-26 13:33:22 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_real_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 样本：
  - Haochen：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
  - Zhongwang：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg`
- 关键 ID：
  - Haochen：file_id=`09c7643a-b14a-4dde-b5d0-e6f9afa51af1`, job_id=`ab2bacf4-2740-42fc-ad0f-c494605e6e73`, part_number=`J2824002-06`
  - Zhongwang：file_id=`a340f99b-d0b9-41a8-b8ba-b7101b672075`, job_id=`f323e28e-054a-4554-b58c-fab380a380b3`, part_number=`J2825002-09`

执行命令：

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_REAL_FORCE_UNIQUE=1

bash scripts/verify_cad_connectors_real_2d.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_cad_connectors_real_2d.log
```

输出（摘要）：

```text
CAD 2D Real Connectors Verification Complete
ALL CHECKS PASSED
```

## Run ALL-55（一键回归：verify_all.sh，全量 + CAD Real Samples + Real 2D Connectors）

- 时间：`2025-12-26 17:28:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 41 / FAIL 0 / SKIP 0`
- 说明：平台管理员开启，包含 Tenant Provisioning、CAD Auto Part、CAD Extractor（stub/external/service）、CAD Real Samples、CAD 2D Real Connectors 全量验证。

执行命令：

```bash
export RUN_CAD_REAL_CONNECTORS_2D=1
export RUN_CAD_REAL_SAMPLES=1
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'
export YUANTUS_STORAGE_TYPE='s3'
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_S3_ACCESS_KEY_ID='minioadmin'
export YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin'
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
export YUANTUS_PLATFORM_TENANT_ID=platform
export YUANTUS_PLATFORM_ORG_ID=platform
export RUN_CAD_AUTO_PART=1
export RUN_CAD_EXTRACTOR_STUB=1
export RUN_CAD_EXTRACTOR_EXTERNAL=1
export RUN_CAD_EXTRACTOR_SERVICE=1
export RUN_TENANT_PROVISIONING=1
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/tmp/EXT-123-External-v2.dwg'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
export CAD_EXTRACTOR_EXPECT_VALUE='EXT-123-External'
export CAD_ML_BASE_URL='http://localhost:8001'
export CAD_REAL_FORCE_UNIQUE=1

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full7.log
```

输出（摘要）：

```text
PASS: 41  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run S5-B-Connector-Coverage-Training-DWG-Haochen-1（Haochen 2D 本地连接器覆盖率）

- 时间：`2025-12-27 08:26:38 +0800`
- 模式：`offline`（本地 connector + SQLite）
- CAD Format：`HAOCHEN`
- Connector：`haochencad`
- 目录：`/Users/huazhou/Downloads/训练图纸/训练图纸`
- 结果：`110 files`
- 覆盖率摘要：
  - `part_number`: 110/110
  - `part_name`: 110/110
  - `material`: 0/110
  - `weight`: 0/110
  - `revision`: 109/110
  - `drawing_no`: 110/110
  - `author`: 0/110
  - `created_at`: 0/110
- 报告：`docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`

执行命令：

```bash
.venv/bin/python scripts/collect_cad_extractor_coverage.py \
  --offline \
  --cad-format HAOCHEN \
  --cad-connector-id haochencad \
  --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
  --extensions dwg \
  --report-title "CAD 2D Connector Coverage Report (Haochen, Offline)" \
  --output docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md
```

## Run S5-B-Connector-Coverage-Training-DWG-Zhongwang-1（中望 2D 本地连接器覆盖率）

- 时间：`2025-12-27 08:26:45 +0800`
- 模式：`offline`（本地 connector + SQLite）
- CAD Format：`ZHONGWANG`
- Connector：`zhongwangcad`
- 目录：`/Users/huazhou/Downloads/训练图纸/训练图纸`
- 结果：`110 files`
- 覆盖率摘要：
  - `part_number`: 110/110
  - `part_name`: 110/110
  - `material`: 0/110
  - `weight`: 0/110
  - `revision`: 109/110
  - `drawing_no`: 110/110
  - `author`: 0/110
  - `created_at`: 0/110
- 报告：`docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`

执行命令：

```bash
.venv/bin/python scripts/collect_cad_extractor_coverage.py \
  --offline \
  --cad-format ZHONGWANG \
  --cad-connector-id zhongwangcad \
  --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
  --extensions dwg \
  --report-title "CAD 2D Connector Coverage Report (Zhongwang, Offline)" \
  --output docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md
```

## Run S5-B-Connector-Coverage-2D-1（回归脚本封装：离线 DWG 覆盖率）

- 时间：`2025-12-27 08:37:50 +0800`
- 脚本：`scripts/verify_cad_connector_coverage_2d.sh`
- 目录：`/Users/huazhou/Downloads/训练图纸/训练图纸`
- 结果：`110 files`
- 覆盖率摘要（Haochen/Zhongwang 一致）：
  - `part_number`: 110/110
  - `part_name`: 110/110
  - `material`: 0/110
  - `weight`: 0/110
  - `revision`: 109/110
  - `drawing_no`: 110/110
  - `author`: 0/110
  - `created_at`: 0/110
- 报告：
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`

执行命令：

```bash
CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
  bash scripts/verify_cad_connector_coverage_2d.sh | tee /tmp/verify_cad_connector_coverage_2d.log
```

## Run ALL-56（一键回归：verify_all.sh + CAD 2D Connector Coverage）

- 时间：`2025-12-27 11:36:20 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 35 / FAIL 0 / SKIP 7`
- 说明：开启 `RUN_CAD_CONNECTOR_COVERAGE_2D=1`，离线覆盖统计纳入回归流程。

执行命令：

```bash
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_with_coverage.log
```

输出（摘要）：

```text
PASS: 35  FAIL: 0  SKIP: 7
ALL TESTS PASSED
```

## Run S5-C-Extractor-External-16（CAD Extractor External：DWG 真实样本）

- 时间：`2025-12-27 11:52:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- Extractor：`http://localhost:8200`
- 样例文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`
  - Job：`bc95425f-d63e-4cb5-8fab-e2f5878d63b0`
  - part_number：`J2824002-06`

执行命令（在回归中触发）：

```bash
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run CAD-REAL-3（真实 CAD 样本：DWG/STEP/PRT）

- 时间：`2025-12-27 11:52:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`ALL CHECKS PASSED`
- 样本：
  - DWG：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
  - STEP：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
  - PRT：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`
- 关键 ID：
  - DWG file_id=`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`, item_number=`J2824002-06`
  - STEP file_id=`a2bc42b4-2057-43b9-bfbd-fd98b7e37c07`, item_number=`CNC`
  - PRT file_id=`40894817-c7ef-49ac-a59d-bca77e8bb090`, item_number=`model2`

执行命令（在回归中触发）：

```bash
RUN_CAD_REAL_SAMPLES=1 \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run ALL-57（一键回归：verify_all.sh + CAD Real Samples + Extractor External）

- 时间：`2025-12-27 11:52:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 36 / FAIL 0 / SKIP 6`
- 说明：开启真实样本与外部 Extractor 验证。

执行命令：

```bash
RUN_CAD_REAL_SAMPLES=1 \
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_real_external.log
```

输出（摘要）：

```text
PASS: 36  FAIL: 0  SKIP: 6
ALL TESTS PASSED
```

## Run ALL-58（一键回归：verify_all.sh + Real 2D Connectors + Coverage + Auto Part）

- 时间：`2025-12-27 12:29:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 39 / FAIL 0 / SKIP 3`
- 说明：开启 Real 2D Connectors、2D 覆盖统计、Auto Part、Extractor Stub/Service。
- SKIP：Extractor External、CAD Real Samples、Tenant Provisioning。

执行命令：

```bash
RUN_CAD_REAL_CONNECTORS_2D=1 \
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_more2.log
```

输出（摘要）：

```text
PASS: 39  FAIL: 0  SKIP: 3
ALL TESTS PASSED
```

## Run ALL-59（一键回归：verify_all.sh + Real 2D Connectors + Coverage + Auto Part + Stub/Service）

- 时间：`2025-12-27 12:29:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 39 / FAIL 0 / SKIP 3`
- 说明：开启 Real 2D Connectors、2D 覆盖统计、Auto Part、Extractor Stub/Service；Auto Part 已修复通过。
- SKIP：Extractor External、CAD Real Samples、Tenant Provisioning。

执行命令：

```bash
RUN_CAD_REAL_CONNECTORS_2D=1 \
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_more2.log
```

输出（摘要）：

```text
PASS: 39  FAIL: 0  SKIP: 3
ALL TESTS PASSED
```

## Run ALL-60（一键回归：verify_all.sh + 外部 Extractor + Real Samples + Tenant Provisioning）

- 时间：`2025-12-27 13:21:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 37 / FAIL 0 / SKIP 5`
- 说明：启用外部 Extractor、真实样本与 Tenant Provisioning；Tenant Provisioning 输出提示 platform admin disabled（脚本内跳过）。
- SKIP：CAD 2D Real Connectors、CAD 2D Connector Coverage、CAD Auto Part、CAD Extractor Stub、CAD Extractor Service。

执行命令：

```bash
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
RUN_CAD_REAL_SAMPLES=1 \
RUN_TENANT_PROVISIONING=1 \
YUANTUS_PLATFORM_ADMIN_ENABLED=true \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_open.log
```

输出（摘要）：

```text
PASS: 37  FAIL: 0  SKIP: 5
ALL TESTS PASSED
```

## Run ALL-61（一键回归：verify_all.sh，启用全部 CAD/Extractor/Provisioning 可选项）

- 时间：`2025-12-27 13:29:28 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 42 / FAIL 0 / SKIP 0`
- 说明：启用 Real 2D Connectors、2D Coverage、Auto Part、Extractor Stub/External/Service、Real Samples、Tenant Provisioning（平台管理员开启）。

执行命令：

```bash
RUN_CAD_REAL_CONNECTORS_2D=1 \
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸 \
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 \
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
RUN_CAD_REAL_SAMPLES=1 \
RUN_TENANT_PROVISIONING=1 \
YUANTUS_PLATFORM_ADMIN_ENABLED=true \
CAD_EXTRACTOR_BASE_URL='http://localhost:8200' \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_EXPECT_KEY='part_number' \
CAD_EXTRACTOR_EXPECT_VALUE='J2824002-06' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_open2.log
```

输出（摘要）：

```text
PASS: 42  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run OPS-HARDENING-20260111-2330（强制配额/审计模式）

- 时间：`2026-01-11 23:30:10 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_hardening.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Search Item：`efb4f56a-315c-410c-a0b7-9eeb7bb093e1`
  - Search Indexed：`1513`
- 说明：
  - Quota：`enforce`
  - Audit：`enabled`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run PACKGO-E2E-20260111-2236（Pack-and-Go sync/async + naming/path/collision）

- 时间：`2026-01-11 22:36:19 +0800`
- 方式：直接调用插件函数（无 HTTP 网络层）
- 结果：sync/async zip 均含 `tree.json`/`manifest.csv`，`export_type=3d` 生效，`collision_strategy=error` 返回 409
- 环境：`sqlite` 临时库 + `local` 存储（`/tmp`）

执行命令（摘要）：

```bash
python3 - <<'PY'
import json
import os
import shutil
import uuid
import zipfile
import importlib.util
import sys
from pathlib import Path

DB_PATH = "/tmp/yuantus_packgo_verify.db"
STORAGE_PATH = "/tmp/yuantus_packgo_storage"
OUTPUT_DIR = "/tmp/yuantus_packgo_output"

for path in [DB_PATH]:
    if os.path.exists(path):
        os.remove(path)
for path in [STORAGE_PATH, OUTPUT_DIR]:
    if os.path.exists(path):
        shutil.rmtree(path)

os.environ["YUANTUS_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["YUANTUS_LOCAL_STORAGE_PATH"] = STORAGE_PATH
os.environ["YUANTUS_SCHEMA_MODE"] = "create_all"

from yuantus.config import get_settings
get_settings.cache_clear()

from sqlalchemy.orm import sessionmaker
from yuantus.database import create_db_engine, init_db
from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.services.file_service import FileService

plugin_path = Path("plugins") / "yuantus-pack-and-go" / "main.py"
spec = importlib.util.spec_from_file_location("pack_and_go_plugin", plugin_path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

engine = create_db_engine()
init_db(create_tables=True, bind_engine=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

session = SessionLocal()
file_service = FileService()

part_type = ItemType(id="Part", label="Part", is_relationship=False)
bom_type = ItemType(
    id="Part BOM",
    label="Part BOM",
    is_relationship=True,
    source_item_type_id="Part",
    related_item_type_id="Part",
)
session.add_all([part_type, bom_type])
session.commit()

root_id = str(uuid.uuid4())
child_id = str(uuid.uuid4())
rel_id = str(uuid.uuid4())
root_version_id = str(uuid.uuid4())

root_item = Item(
    id=root_id,
    item_type_id="Part",
    config_id=f"cfg-{root_id}",
    properties={"item_number": "ASM-001"},
)
child_item = Item(
    id=child_id,
    item_type_id="Part",
    config_id=f"cfg-{child_id}",
    properties={"item_number": "PRT-002", "revision": "C"},
)
relationship = Item(
    id=rel_id,
    item_type_id="Part BOM",
    config_id=f"cfg-{rel_id}",
    source_id=root_id,
    related_id=child_id,
    properties={"quantity": 2},
)

session.add_all([root_item, child_item, relationship])
session.commit()

root_version = ItemVersion(
    id=root_version_id,
    item_id=root_id,
    revision="B",
    generation=1,
    version_label="1.B",
)
session.add(root_version)
session.commit()

root_item.current_version_id = root_version_id
session.add(root_item)
session.commit()

os.makedirs(STORAGE_PATH, exist_ok=True)

def add_file(filename, system_path, document_type, file_role, item_id):
    full_path = os.path.join(STORAGE_PATH, system_path)
    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "wb") as handle:
        handle.write(f"{filename}".encode("utf-8"))
    file_id = str(uuid.uuid4())
    container = FileContainer(
        id=file_id,
        filename=filename,
        file_type=Path(filename).suffix.lstrip(".") or "dat",
        system_path=system_path,
        file_size=os.path.getsize(full_path),
        document_type=document_type,
    )
    session.add(container)
    item_file = ItemFile(
        id=str(uuid.uuid4()),
        item_id=item_id,
        file_id=file_id,
        file_role=file_role,
    )
    session.add(item_file)

add_file("asm.step", "files/asm.step", "3d", "native_cad", root_id)
add_file("asm.step", "files/asm_copy.step", "3d", "native_cad", root_id)
add_file("child.step", "files/child.step", "3d", "native_cad", child_id)
session.commit()

file_roles, doc_types, include_printouts, include_geometry, _ = module._resolve_export_preset(
    export_type="3d",
    file_roles=None,
    document_types=None,
    include_printouts=True,
    include_geometry=True,
    fields_set=set(),
)

result = module.build_pack_and_go_package(
    session,
    item_id=root_id,
    depth=-1,
    file_roles=file_roles,
    document_types=doc_types,
    include_previews=False,
    include_printouts=include_printouts,
    include_geometry=include_geometry,
    filename_mode=module._normalize_filename_mode("item_number_rev"),
    path_strategy=module._normalize_path_strategy("item"),
    collision_strategy=module._normalize_collision_strategy("append_counter"),
    include_bom_tree=True,
    bom_tree_filename="tree.json",
    include_manifest_csv=True,
    manifest_csv_filename="manifest.csv",
    output_dir=Path(OUTPUT_DIR),
    file_service=file_service,
)

with zipfile.ZipFile(result.zip_path, "r") as zipf:
    names = sorted(zipf.namelist())
print("[SYNC] zip entries:", names)

try:
    module.build_pack_and_go_package(
        session,
        item_id=root_id,
        depth=-1,
        file_roles=file_roles,
        document_types=doc_types,
        include_previews=False,
        include_printouts=include_printouts,
        include_geometry=include_geometry,
        filename_mode=module._normalize_filename_mode("item_number_rev"),
        path_strategy=module._normalize_path_strategy("item"),
        collision_strategy=module._normalize_collision_strategy("error"),
        output_dir=Path(OUTPUT_DIR),
        file_service=file_service,
    )
except Exception as exc:
    print("[ERROR] collision_strategy=error raised:", exc)

payload = {
    "item_id": root_id,
    "depth": -1,
    "export_type": "3d",
    "include_previews": False,
    "include_printouts": include_printouts,
    "include_geometry": include_geometry,
    "filename_mode": "item_number_rev",
    "path_strategy": "item",
    "collision_strategy": "append_counter",
    "include_bom_tree": True,
    "bom_tree_filename": "tree.json",
    "include_manifest_csv": True,
    "manifest_csv_filename": "manifest.csv",
}

async_result = module.handle_pack_and_go_job(payload, session)
with zipfile.ZipFile(async_result["zip_path"], "r") as zipf:
    async_names = sorted(zipf.namelist())
print("[ASYNC] zip entries:", async_names)
session.close()
PY
```

输出（摘要）：

```text
[SYNC] zip entries: ['ASM-001/ASM-001_B.step', 'ASM-001/ASM-001_B_1.step', 'PRT-002/PRT-002_C.step', 'manifest.csv', 'manifest.json', 'tree.json']
[ERROR] collision_strategy=error raised: 409: Path collision: ASM-001/ASM-001_B.step
[ASYNC] zip entries: ['ASM-001/ASM-001_B.step', 'ASM-001/ASM-001_B_1.step', 'PRT-002/PRT-002_C.step', 'manifest.csv', 'manifest.json', 'tree.json']
```

## Run CAD-IMPORT-DEFAULT-20260110-2240（CAD Import 默认仅 preview+extract）

- 时间：`2026-01-10 22:40:58 +0800`
- 基地址：`http://127.0.0.1:7910`
- 方式：手动验证
- 结果：`PASS`
- 关键 ID：
  - File：`763b98a4-4126-4dd8-aabb-092c486f97aa`
  - Jobs：`cad_preview=04bbf67c-e445-4ba1-86e3-382ca8cffdc7`，`cad_extract=e8347b49-d872-4a10-a9ab-77069866a42f`

执行要点：

```bash
# 导入文件（不传 create_geometry_job/create_dedup_job）
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1" \
  -F "file=@/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg"

# 断言：jobs 仅包含 cad_preview、cad_extract
# cad_metadata 返回 302，attributes 返回 200
curl -s -o /dev/null -w "%{http_code}" \
  http://127.0.0.1:7910/api/v1/file/763b98a4-4126-4dd8-aabb-092c486f97aa/cad_metadata
curl -s -o /dev/null -w "%{http_code}" \
  http://127.0.0.1:7910/api/v1/cad/files/763b98a4-4126-4dd8-aabb-092c486f97aa/attributes
```

## Run BOM-UI-20260111-2218（BOM UI 关键接口）

- 时间：`2026-01-11 22:18:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_ui.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Substitute：`8122c0c0-141c-43ad-84a7-12b1e1dbb013`

执行命令：

```bash
bash scripts/verify_bom_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run PRODUCT-DETAIL-20260111-2219（产品详情聚合）

- 时间：`2026-01-11 22:19:52 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_product_detail.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`904e013f-7c84-4fb0-8398-d94bc132ea6b`
  - Version：`bd3b6842-0c9b-4062-89c9-01acc3277e3f`
  - File：`7364e79e-b500-4683-88d8-72e2af449d81`

执行命令：

```bash
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run DOCS-APPROVAL-20260111-2221（文档流程 + ECO 审批）

- 时间：`2026-01-11 22:21:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_docs_approval.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`a835ac75-dfde-402e-9a11-3c7e79b1c4c4`
  - File：`856c95c3-be7d-439d-939b-a8cf10d2f5c0`
  - Document：`e23f48e6-a7e3-43b6-b965-52734a4676c8`
  - ECO Stage：`1e1e08c3-9ca7-4b0d-b24d-56daea8d1c4a`
  - ECO Product：`a2519c80-bcaa-4971-a4d5-432a0c5707b8`
  - ECO：`47134299-8409-49c0-af19-c5a3a869ac5a`
  - ECO Approval：`6b6d01a3-ae09-4e2e-a8fa-02a2884a1416`

执行命令：

```bash
bash scripts/verify_docs_approval.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run SEARCH-REINDEX-20260111-2222（索引状态 + 重建）

- 时间：`2026-01-11 22:22:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_search_reindex.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Item：`f7c7b21c-2b91-4e95-af83-c5b53fc7ed8c`
  - Engine：`db`
  - Indexed：`361`

执行命令：

```bash
bash scripts/verify_search_reindex.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run TENANT-PROVISION-20260111-2225（平台管理员创建租户）

- 时间：`2026-01-11 22:25:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Tenant：`tenant-provision-1768141491`
  - Org：`org-provision-1768141491`
  - Extra Org：`org-extra-1768141491`
  - Admin：`admin-1768141491`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-CONNECTORS-20260111-2226（CAD 连接器：2D 合成样本）

- 时间：`2026-01-11 22:26:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GSTARCAD：`66832fbc-163b-46ed-9a67-567585af6404`
  - ZWCAD：`6cfa0b1e-e075-4ec7-9928-88e027a3fd11`
  - HAOCHEN：`5a78856b-6e6a-4751-a745-f7d83d9aa04d`
  - ZHONGWANG：`a084ccdc-a1e1-4ba6-a916-c4bdb5e14e66`
  - Auto Detect 1：`9c85c29e-c1c4-42a5-94a5-591ad6c059ee`
  - Auto Detect 2：`78aead16-147a-438e-b313-f452d782e777`
- 说明：`RUN_REAL=0`，真实样本验证跳过。

执行命令：

```bash
bash scripts/verify_cad_connectors.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run OPS-HARDENING-20260111-2233（多租户/配额/审计/健康/索引）

- 时间：`2026-01-11 22:33:23 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_hardening.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Search Item：`0f2b4c9d-4f63-45fb-aeea-38b12591943e`
  - Search Indexed：`1485`
- 说明：
  - Quota：`SKIP`（quota mode=disabled）
  - Audit：`SKIP`（audit_enabled=false）

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run BOM-COMPARE-FIELDS-20260111-2248（BOM Compare 字段级对照）

- 时间：`2026-01-11 22:48:04 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_bom_compare_fields.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Left Item：`99ea07d1-74b7-4e73-a310-029cdc4f37c8`
  - Right Item：`8712b5d7-94bd-4c4f-9337-d7c8025f0c0b`
  - Child Item：`1476fb78-9cbb-453f-9a59-82b170a9aeff`
  - Substitute Item：`4c180b49-63a0-4422-bd6b-2d4235df5ec8`
  - Left BOM Line：`15372c3f-1ca2-4803-9e85-a87cbfb706b1`
  - Right BOM Line：`437fb3ce-d1f6-46d5-8326-a10bca27d2af`
  - Substitute Rel：`c730b881-ee75-4c54-b817-174e0c7f9998`

执行命令：

```bash
bash scripts/verify_bom_compare_fields.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run PRODUCT-UI-20260111-2253（产品详情 UI 聚合）

- 时间：`2026-01-11 22:53:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_product_ui.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Parent Item：`7f809f0c-3df7-4b4f-bd78-03b9f5dbab85`
  - Child Item：`59218840-a871-4654-988e-a594e7d81e8c`
  - BOM Line：`8b822076-74a0-4ac3-9d90-957f3c5ae839`

执行命令：

```bash
bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run WHERE-USED-UI-20260111-2300（Where-Used UI 输出）

- 时间：`2026-01-11 23:00:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_where_used_ui.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Grand：`1a185290-44c8-453e-a7de-56b56ae8cb67`
  - Parent：`a2ae62cb-e9dc-4cbb-9160-4b3e1de2a17b`
  - Child：`214a693b-27f9-4246-89f1-d78829d110fe`
  - Parent BOM：`63c88952-92e0-448d-b363-0701393e5b7d`
  - Grand BOM：`c070a8e6-effc-4371-bb3a-be5bb360bc7b`

执行命令：

```bash
bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run DOCS-ECO-UI-20260111-2313（文档/审批聚合）

- 时间：`2026-01-11 23:13:32 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_docs_eco_ui.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`cc64c49b-5d51-48a7-9ec2-6bea074f91b6`
  - Document：`da1f08bc-638b-4d8b-8dae-d87c2594c7b3`
  - ECO：`563298f8-0e3b-4a5f-b1b3-1777a225387d`
  - ECO Stage：`7c7e7c12-b607-4a9e-a931-947defe7cae4`

执行命令：

```bash
bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-IMPORT-DEFAULT-20260110-2200（CAD Import Default: Preview + Extract）

- 时间：`2026-01-10 22:00:16 +0800`
- 基地址：`http://127.0.0.1:7910`
- 文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg`
- 关键 ID：File `763b98a4-4126-4dd8-aabb-092c486f97aa`; Jobs `cad_preview=71b7f1c3-3b7a-4879-939f-3081e337b7fd`, `cad_extract=85f2aafe-5aba-4728-a2d5-ff508f1e8e0f`
- 结果：默认只创建 preview + extract 两个任务；cad_metadata `302`（S3 presigned），attributes `200`

执行命令：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg"

for endpoint in \
  "/api/v1/file/763b98a4-4126-4dd8-aabb-092c486f97aa/cad_metadata" \
  "/api/v1/cad/files/763b98a4-4126-4dd8-aabb-092c486f97aa/attributes"; do
  curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:7910${endpoint}" \
    -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' -H "Authorization: Bearer $TOKEN"
done
```

## Run CAD-EXTRACT-METADATA-20260110-2121（CAD Extract Metadata + Mesh Stats Guard）

- 时间：`2026-01-10 21:21:50 +0800`
- 基地址：`http://127.0.0.1:7910`
- 文件：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
- 关键 ID：File `c1fb5877-5316-459e-8f4c-14dd2a2fca26`; Jobs `cad_preview=1fbbf8b9-9612-40c5-b756-061a638e0009`, `cad_geometry=760cb173-60cd-468a-9090-64b49fb3bb63`, `cad_extract=a567f3e7-b29d-4cf8-9ec0-36f2b48b8444`, `cad_dedup_vision=f65aab5b-cd83-41e1-9717-d08bff11c47b`
- 结果：cad_metadata `302`（S3 presigned），attributes `200`，mesh-stats `404`（cad_attributes guard 生效），geometry `404`（DWG converter 未配置，预期），cad_geometry 报错 `DWG converter not configured. Set YUANTUS_DWG_CONVERTER_BIN.`，cad_dedup_vision `400`（外部服务未配置）

执行命令：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg" \
  -F "create_preview_job=true" \
  -F "create_geometry_job=true" \
  -F "create_extract_job=true"

for endpoint in \
  "/api/v1/file/c1fb5877-5316-459e-8f4c-14dd2a2fca26/cad_metadata" \
  "/api/v1/cad/files/c1fb5877-5316-459e-8f4c-14dd2a2fca26/attributes" \
  "/api/v1/cad/files/c1fb5877-5316-459e-8f4c-14dd2a2fca26/mesh-stats" \
  "/api/v1/file/c1fb5877-5316-459e-8f4c-14dd2a2fca26/geometry"; do
  curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:7910${endpoint}" \
    -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' -H "Authorization: Bearer $TOKEN"
done
```

## Run ALL-62（一键回归：run_full_regression.sh 全量回归）

- 时间：`2025-12-27 13:53:40 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/run_full_regression.sh`
- 结果：`PASS 42 / FAIL 0 / SKIP 0`
- 说明：使用一键全量回归脚本，包含 CAD Connectors/Extractor/Real Samples/Tenant Provisioning 全部可选项。

执行命令：

```bash
scripts/run_full_regression.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_open3.log
```

输出（摘要）：

```text
PASS: 42  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run H-20251227-Integrations（Run H：独立 Athena 认证头）

- 时间：`2025-12-27 17:10:39 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_run_h.sh`
- 结果：`PASS`
- 说明：使用 `X-Athena-Authorization`，并为本机环境覆盖 DB URL 与 tenancy 配置；`cad_ml/dedup_vision` 未启用，`integrations ok=false` 但 `athena ok=true`。

执行命令：

```bash
TENANCY_MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
ATHENA_AUTH_TOKEN='<athena_token>' \
  bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
Integrations health: OK (ok=False)
```

## Run H-20251228-1405（Run H：Core APIs 快速回归）

- 时间：`2025-12-28 14:05:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_run_h.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：API 运行于 `db-per-tenant-org` + Postgres + MinIO；`integrations ok=false`（外部服务未启用）。
- 关键 ID：
  - Part：`e12b331f-a37d-45ac-9af5-b53a5414ab7e`
  - RPC Part：`3a41af12-f804-4d21-b59d-398b051e84f9`
  - File：`6af009b1-686a-4829-92dc-f7881940caa4`
  - ECO Stage：`8b1e7258-b4e2-4bab-9f2d-b37fba253309`
  - ECO：`0f24fd54-a361-404e-9882-3dc17c5244af`
  - Version：`eb9454d1-7bea-4b89-8e69-7a96ce84ee58`

执行命令：

```bash
TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Integrations health: OK (ok=False)
ALL CHECKS PASSED
```

## Run ALL-20260119-1134（verify_all.sh 全量回归）

- 时间：`2026-01-19 11:34:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`
- 结果：`PASS 32 / FAIL 0 / SKIP 11`
- 说明：`CAD ML Vision` 未启用，相关步骤跳过；CAD Extractor 外部地址不可达时脚本回退本地处理。

执行命令：

```bash
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 32  FAIL: 0  SKIP: 11
ALL TESTS PASSED
```

## Run S7-20260119-1203（Multi-Tenancy Isolation）

- 时间：`2026-01-19 12:03:33 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_multitenancy.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：运行于 `db-per-tenant-org`，验证 tenant/org 隔离。

执行命令：

```bash
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run OPS-20251228-1405（Ops Health 依赖检查）

- 时间：`2025-12-28 14:05:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_health.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_ops_health.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
OK: /health ok
OK: /health/deps ok
ALL CHECKS PASSED
```

## Run CAD-2D-20251228-2133（CAD 2D Connectors）

- 时间：`2025-12-28 21:33:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - GStarCAD：`d7683e55-8484-41fa-9cc8-b1ab0750d296`
  - ZWCAD：`1bdcaa93-1d3f-4ef8-8453-3f46580858b8`
  - Haochen：`14c1433d-4631-4fdc-a6b3-cbc883a07299`
  - Zhongwang：`26a268be-103d-4141-8d81-289e323a3f6a`
  - Auto(Haochen)：`8bca837b-3c9d-4a78-8c5e-27fa05c228db`
  - Auto(ZWCAD)：`e489f0e4-e23c-4097-9ceb-fbedc65e97c4`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-3D-20251228-2133（CAD 3D Connectors）

- 时间：`2025-12-28 21:33:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_3d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - SolidWorks Part：`a0f3a4e2-0e3a-48e3-b23f-d41695f7bdbc`
  - SolidWorks ASM：`4e0ef6ed-bf45-4cfb-b5d6-580588031e19`
  - NX PRT：`f2701bcc-01bf-4475-92b9-436b2e235f38`
  - Creo PRT：`59b29fdf-39cd-4756-8d1b-e6cf65a566e4`
  - CATIA：`02ae741c-e0b9-4f89-b665-9838643b7405`
  - Inventor：`5bebcb64-609a-4625-8cb7-4a42091105b4`
  - Auto(NX)：`0de3b98d-5c62-4c01-8e37-e64decca3aa4`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_connectors_3d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-2D-REAL-20251228-2134（CAD 2D Real Samples）

- 时间：`2025-12-28 21:34:04 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_real_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Haochen：`file_id=09c7643a-b14a-4dde-b5d0-e6f9afa51af1`, `job_id=aa49569f-5742-4641-91da-7ef926e2898e`
  - Zhongwang：`file_id=a340f99b-d0b9-41a8-b8ba-b7101b672075`, `job_id=05099a7b-c2a8-4365-a2c2-34bcda1c6fb1`

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_connectors_real_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-NORM-20251228-2151（CAD 属性归一化）

- 时间：`2025-12-28 21:51:49 +0800`
- 脚本：`scripts/verify_cad_attribute_normalization.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：本地 SQLite + 本地存储。

执行命令：

```bash
bash scripts/verify_cad_attribute_normalization.sh
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-FILENAME-20251228-2152（CAD 文件名解析）

- 时间：`2025-12-28 21:52:03 +0800`
- 脚本：`scripts/verify_cad_filename_parse.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：本地 SQLite + 本地存储。

执行命令：

```bash
bash scripts/verify_cad_filename_parse.sh
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACT-LOCAL-20251228-2152（CAD 本地提取）

- 时间：`2025-12-28 21:52:12 +0800`
- 脚本：`scripts/verify_cad_extract_local.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：本地 SQLite + 本地存储。

执行命令：

```bash
bash scripts/verify_cad_extract_local.sh
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-SYNC-20251228-2152（CAD 属性同步）

- 时间：`2025-12-28 21:52:25 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - Part：`daf086ff-8628-4b2e-b90a-1f80f571b2f9`
  - File：`740494a5-befc-49a8-a505-bcb55a9d6eaf`
  - Job：`0d058c0d-aaa2-46c2-827d-a10dcf723221`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-REAL-20251228-2152（CAD Real Samples）

- 时间：`2025-12-28 21:52:42 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_real_samples.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - DWG：`file_id=46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`, `item_id=cc4809a5-6ad5-419d-b9f1-8e6bb7582e09`
  - STEP：`file_id=a2bc42b4-2057-43b9-bfbd-fd98b7e37c07`, `item_id=cdaffdde-9824-4232-b8fa-231f4fe24c81`
  - PRT：`file_id=40894817-c7ef-49ac-a59d-bca77e8bb090`, `item_id=b4fa56e2-a7a7-47ab-8dd6-9c21d9b9d01b`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACTOR-STUB-20251228-2224（CAD Extractor Stub）

- 时间：`2025-12-28 22:24:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_stub.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`cf7efbf1-723f-466a-ad47-6b616c6e7fd1`
  - Job：`b1da373a-df76-4b9b-8501-67edeac362f5`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-CONNECTORS-CONFIG-20251228-2224（CAD Connectors Config）

- 时间：`2025-12-28 22:24:20 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_config.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`3809b563-91d1-4c10-893b-e412eedb9d89`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-SYNC-TEMPLATE-20251228-2224（CAD Sync Template）

- 时间：`2025-12-28 22:24:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync_template.sh`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_cad_sync_template.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-PIPELINE-S3-20251228-2224（CAD Pipeline S3）

- 时间：`2025-12-28 22:24:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_pipeline_s3.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`6520876b-cd7e-4132-9cdf-df47f9bcf3af`
  - Preview Job：`3a231d60-105d-44b2-91d8-c17499a1bc04`
  - Geometry Job：`c57e6069-1fe5-446b-ab40-f423830d6c9f`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-MISSING-SOURCE-20251228-2225（CAD Missing Source）

- 时间：`2025-12-28 22:25:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_missing_source.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`8e94c35c-cf57-4773-8d63-345061c47708`
  - Job：`b9cb10de-c69d-4de3-a975-d6507800863d`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_missing_source.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-PREVIEW-2D-20251228-2225（CAD Preview 2D）

- 时间：`2025-12-28 22:25:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 结果：`ALL CHECKS PASSED`
- 关键 ID：
  - File：`46e9ad31-d9f8-4e9e-8617-c9b7b6f34fe9`

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
  bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run ALL-63（一键回归：run_full_regression.sh 全量回归）

- 时间：`2026-01-05 16:15:12 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/run_full_regression.sh`
- 结果：`PASS 42 / FAIL 0 / SKIP 0`
- 日志：`/tmp/verify_all_full_20260105_161403.log`
- 说明：同步运行服务的 DB 配置并修复迁移兼容/Auto Part 校验后，执行全量回归通过。

执行命令：

```bash
scripts/run_full_regression.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_20260105_161403.log
```

输出（摘要）：

```text
PASS: 42  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run P（插件增强回归测试）

- 时间：`2026-01-11 23:34:14 +0800`
- 说明：验证 BOM Compare 与 Pack-and-Go 插件单测覆盖新增功能。

```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py   src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```

```text
27 passed, 1 skipped in 0.34s
```

## Run PACKGO-PROGRESS-20260112-1014（插件配置迁移 + Pack-and-Go 进度）

- 时间：`2026-01-12 10:14:03 +0800`
- 说明：升级迁移到 plugin configs 表，验证 pack-and-go 异步进度回写（file_scope=version），并重跑插件单测。

### 1) DB 迁移到 Head

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=sqlite:///./yuantus_dev_verify.db \
  python3 -m alembic -c alembic.ini upgrade head
```

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade h1b2c3d4e5f6 -> i1b2c3d4e5f7, add cad document schema version and properties
INFO  [alembic.runtime.migration] Running upgrade i1b2c3d4e5f7 -> j1b2c3d4e5f8, add cad view state
INFO  [alembic.runtime.migration] Running upgrade j1b2c3d4e5f8 -> k1b2c3d4e5f9, add cad review fields
INFO  [alembic.runtime.migration] Running upgrade k1b2c3d4e5f9 -> l1b2c3d4e6a0, add cad change logs
INFO  [alembic.runtime.migration] Running upgrade l1b2c3d4e6a0 -> m1b2c3d4e6a1, add plugin configs
```

### 2) 确认插件配置表

```bash
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('yuantus_dev_verify.db')
rows = list(conn.execute("select name from sqlite_master where type='table' and name='meta_plugin_configs'"))
print(rows)
conn.close()
PY
```

```text
[('meta_plugin_configs',)]
```

### 3) Seed Meta Schema（Part/Part BOM/Document）

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=sqlite:///./yuantus_dev_verify.db \
  python3 -m yuantus.cli seed-meta
```

```bash
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('yuantus_dev_verify.db')
rows = list(conn.execute("select id from meta_item_types where id in ('Part','Document','Part BOM') order by id"))
print(rows)
conn.close()
PY
```

```text
[('Document',), ('Part',), ('Part BOM',)]
```

### 4) Pack-and-Go 异步进度（file_scope=version）

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=sqlite:///./yuantus_dev_verify.db python3 - <<'PY'
import json
import sys
import uuid
from pathlib import Path
import importlib.util

from yuantus.config import get_settings
from yuantus.database import SessionLocal
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.models import ItemVersion, VersionFile
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.job_service import JobService

import_all_models()

session = SessionLocal()
try:
    settings = get_settings()
    base_path = Path(settings.LOCAL_STORAGE_PATH)
    rel_path = Path("packgo_verify") / "part.step"
    full_path = base_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text("packgo verify file\n", encoding="utf-8")
    size = full_path.stat().st_size

    file_id = str(uuid.uuid4())
    item_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    file_entry = FileContainer(
        id=file_id,
        filename="part.step",
        file_type="step",
        mime_type="model/step",
        file_size=size,
        system_path=str(rel_path),
        document_type="3d",
        is_native_cad=True,
    )
    session.add(file_entry)

    item = Item(
        id=item_id,
        item_type_id="Part",
        config_id=item_id,
        generation=1,
        is_current=True,
        state="Released",
        is_versionable=True,
        properties={"item_number": "P-PACKGO-001", "name": "PackGo Verify"},
    )
    session.add(item)

    version = ItemVersion(
        id=version_id,
        item_id=item_id,
        generation=1,
        revision="A",
        version_label="1.A",
        state="Released",
        is_current=True,
    )
    session.add(version)
    session.flush()
    item.current_version_id = version_id

    vfile = VersionFile(
        id=str(uuid.uuid4()),
        version_id=version_id,
        file_id=file_id,
        file_role="native_cad",
        sequence=0,
        is_primary=True,
    )
    session.add(vfile)
    session.commit()

    plugin_path = Path.cwd() / "plugins" / "yuantus-pack-and-go" / "main.py"
    spec = importlib.util.spec_from_file_location("packgo_plugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    payload = {
        "item_id": item_id,
        "depth": 0,
        "file_scope": "version",
        "file_roles": ["native_cad"],
        "document_types": ["3d"],
        "include_previews": False,
        "include_printouts": False,
        "include_geometry": False,
        "include_manifest_csv": True,
        "manifest_csv_columns": [
            "file_id",
            "source_item_number",
            "source_version_id",
            "item_revision",
        ],
    }

    job_service = JobService(session)
    job = job_service.create_job("pack_and_go", payload, user_id=1)
    result = module.handle_pack_and_go_job(payload, session, job_id=job.id)
    job_service.complete_job(job.id, result)
    job = job_service.get_job(job.id)

    print("job_id", job.id)
    print("status", job.status)
    print("progress", json.dumps(job.payload.get("progress"), ensure_ascii=True))
    print("zip_path", job.payload.get("result", {}).get("zip_path"))
finally:
    session.close()
PY
```

```text
job_id 0fee06c6-824f-4271-a7ab-253195c306f8
status completed
progress {"stage": "complete", "current": 1, "total": 1, "percent": 100, "updated_at": "2026-01-12T02:13:04.636813", "message": "complete", "extra": {"file_count": 1, "total_bytes": 19, "duration_sec": 0.009}}
zip_path tmp/pack_and_go/pack_and_go_P-PACKGO-001_20260112021304.zip
```

### 5) 插件单测回归

```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```

```text
27 passed, 1 skipped in 1.45s
```

## Run PACKGO-TEST-20260112-1326（Pack-and-Go 映射单测）

- 时间：`2026-01-12 13:26:04 +0800`
- 说明：新增 `file_scope=version` 的映射单测覆盖。

```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py
```

```text
19 passed in 0.30s
```

## Run PLUGIN-TESTS-20260112-1310（插件单测回归）

- 时间：`2026-01-12 13:10:16 +0800`
- 脚本：`pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py src/yuantus/meta_engine/tests/test_plugin_bom_compare.py`
- 结果：`27 passed, 1 skipped`

执行命令：

```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```

输出（摘要）：

```text
27 passed, 1 skipped in 1.44s
```

## Run PLUGIN-VERIFY-20260112-1649（插件回归 + 迁移验证）

- 时间：`2026-01-12 16:49:23 +0800`
- 说明：插件单测回归 + SQLite 临时库迁移到 head（`tmp/verify_plugin.db`）。

### 1) DB 迁移到 Head

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=sqlite:///./tmp/verify_plugin.db \
  python3 -m alembic -c alembic.ini upgrade head
```

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> f87ce5711ce1, initial schema
INFO  [alembic.runtime.migration] Running upgrade f87ce5711ce1 -> e5c1f9a4b7d2, add eco stage sla hours
INFO  [alembic.runtime.migration] Running upgrade e5c1f9a4b7d2 -> a1b2c3d4e5f6, add audit logs
INFO  [alembic.runtime.migration] Running upgrade a1b2c3d4e5f6 -> b7c9d2e1f4a6, add cad connector id and job dedupe key
INFO  [alembic.runtime.migration] Running upgrade b7c9d2e1f4a6 -> c9d4e6f7a8b9, add cad attributes storage
INFO  [alembic.runtime.migration] Running upgrade c9d4e6f7a8b9 -> d4f1a2b3c4d5, add baselines
INFO  [alembic.runtime.migration] Running upgrade d4f1a2b3c4d5 -> g8f9a0b1c2d3, add_tenant_quotas
INFO  [alembic.runtime.migration] Running upgrade g8f9a0b1c2d3 -> f1a2b3c4d5e6, add file metadata columns
INFO  [alembic.runtime.migration] Running upgrade f1a2b3c4d5e6 -> h1b2c3d4e5f6, add cadgf artifact paths
INFO  [alembic.runtime.migration] Running upgrade h1b2c3d4e5f6 -> i1b2c3d4e5f7, add cad document schema version and properties
INFO  [alembic.runtime.migration] Running upgrade i1b2c3d4e5f7 -> j1b2c3d4e5f8, add cad view state
INFO  [alembic.runtime.migration] Running upgrade j1b2c3d4e5f8 -> k1b2c3d4e5f9, add cad review fields
INFO  [alembic.runtime.migration] Running upgrade k1b2c3d4e5f9 -> l1b2c3d4e6a0, add cad change logs
INFO  [alembic.runtime.migration] Running upgrade l1b2c3d4e6a0 -> m1b2c3d4e6a1, add plugin configs
```

### 2) 插件单测回归

```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```

```text
28 passed, 1 skipped in 1.64s
```

## Run ALL-64（一键回归：verify_all.sh，主干合并后）

- 时间：`2026-01-12 16:51:59 +0800`
- 脚本：`scripts/verify_all.sh`
- 环境：`BASE_URL=http://127.0.0.1:7910`，`TENANT=tenant-1`，`ORG=org-1`
- 结果：`PASS 34 / FAIL 0 / SKIP 9`

跳过项（均为可选开关未开启）：

- `S5-A (CADGF Preview Online)`（`RUN_CADGF_PREVIEW_ONLINE=0`）
- `S5-B (CAD 2D Real Connectors)`（`RUN_CAD_REAL_CONNECTORS_2D=0`）
- `S5-B (CAD 2D Connector Coverage)`（`RUN_CAD_CONNECTOR_COVERAGE_2D=0`）
- `S5-C (CAD Auto Part)`（`RUN_CAD_AUTO_PART=0`）
- `S5-C (CAD Extractor Stub)`（`RUN_CAD_EXTRACTOR_STUB=0`）
- `S5-C (CAD Extractor External)`（`RUN_CAD_EXTRACTOR_EXTERNAL=0`）
- `S5-C (CAD Extractor Service)`（`RUN_CAD_EXTRACTOR_SERVICE=0`）
- `CAD Real Samples`（`RUN_CAD_REAL_SAMPLES=0`）
- `S7 (Tenant Provisioning)`（`RUN_TENANT_PROVISIONING=0`）

说明：

- `CAD ML Vision` 未启用时，2D 预览与 OCR 标题栏脚本输出提示为 skip，但整体统计为 PASS。

```text
PASS: 34  FAIL: 0  SKIP: 9
ALL TESTS PASSED
```

## Run TENANT-PROVISION-20260112-2137（租户开通/组织创建）

- 时间：`2026-01-12 21:37:48 +0800`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 环境：`BASE_URL=http://127.0.0.1:7910`

```bash
bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run CAD-REAL-SAMPLES-20260112-2137（真实样本 CAD 导入/预览/抽取）

- 时间：`2026-01-12 21:37:48 +0800`
- 脚本：`scripts/verify_cad_real_samples.sh`
- 环境：`BASE_URL=http://127.0.0.1:7910`，S3 storage（MinIO: `http://localhost:59000`）
- 样本：
  - DWG：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
  - STEP：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
  - PRT：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`

```bash
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACTOR-SERVICE-20260112-2143（Extractor 服务直连）

- 时间：`2026-01-12 21:43:42 +0800`
- 脚本：`scripts/verify_cad_extractor_service.sh`
- 环境：`CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200`

```bash
bash scripts/verify_cad_extractor_service.sh
```

```text
ALL CHECKS PASSED
```

## Run CAD-EXTRACTOR-EXTERNAL-20260112-2143（外部 Extractor 接入）

- 时间：`2026-01-12 21:43:42 +0800`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 环境：`TENANCY=db-per-tenant-org`，S3 storage（MinIO: `http://localhost:59000`）
- 样本：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
CAD_EXTRACTOR_BASE_URL=http://localhost:8200 \
CAD_EXTRACTOR_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg" \
bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run CAD-REAL-CONNECTORS-2D-20260112-2143（2D 实际连接器：浩辰/中望）

- 时间：`2026-01-12 21:43:42 +0800`
- 脚本：`scripts/verify_cad_connectors_real_2d.sh`
- 环境：`TENANCY=db-per-tenant-org`，S3 storage（MinIO: `http://localhost:59000`）
- 样本：
  - `CAD_SAMPLE_HAOCHEN_DWG=/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
  - `CAD_SAMPLE_ZHONGWANG_DWG=/Users/huazhou/Downloads/训练图纸/训练图纸/J2825002-09下轴承支架组件v2.dwg`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_CAD_EXTRACTOR_BASE_URL=http://localhost:8200 \
YUANTUS_CAD_EXTRACTOR_MODE=required \
bash scripts/verify_cad_connectors_real_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run ALL-65（verify_all.sh 全量回归：可选项全开）

- 时间：`2026-01-13 10:46:52 +0800`
- 脚本：`scripts/verify_all.sh`
- 日志：`/tmp/verify_all_full_optional_20260113_1045.log`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `S3=MinIO http://localhost:59000`
  - `CAD_EXTRACTOR_BASE_URL=http://localhost:8200`
  - `CAD_ML_BASE_URL=http://localhost:8000`
  - `CADGF_PREVIEW_SAMPLE_FILE=/Users/huazhou/Downloads/新建文件夹/converted/J0224022-06上罐体组件v1.dxf`
  - `CAD_CONNECTOR_COVERAGE_DIR=/Users/huazhou/Downloads/训练图纸/训练图纸`

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_S3_BUCKET_NAME=yuantus \
CAD_EXTRACTOR_BASE_URL=http://localhost:8200 \
YUANTUS_CAD_EXTRACTOR_BASE_URL=http://localhost:8200 \
CAD_ML_BASE_URL=http://localhost:8000 \
CADGF_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/新建文件夹/converted/J0224022-06上罐体组件v1.dxf" \
CAD_CONNECTOR_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸" \
CAD_CONNECTOR_COVERAGE_MAX_FILES=30 \
RUN_CADGF_PUBLIC_BASE=1 \
RUN_CADGF_PREVIEW_ONLINE=1 \
RUN_CAD_REAL_CONNECTORS_2D=1 \
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 \
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
RUN_CAD_REAL_SAMPLES=1 \
RUN_TENANT_PROVISIONING=1 \
CADGF_SYNC_GEOMETRY=1 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
PASS: 43  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```

## Run H-20260119-1014（Run H：Compose 基线回归）

- 时间：`2026-01-19 10:14:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_run_h.sh`
- 结果：`ALL CHECKS PASSED`
- 说明：使用 docker compose 启动服务（Postgres + MinIO + API + Worker），通过临时 CLI wrapper 执行 seed。
- 关键 ID：
  - Part：`4fe2cc74-6804-4924-a3d9-7053e30846ae`
  - RPC Part：`86e1743d-e3c9-40ee-a287-b25b805aeb77`
  - File：`a47baa5f-7431-4a09-a8eb-acbc0b1096ad`
  - ECO Stage：`abbad498-87e4-4cca-8012-a6d4512d7f18`
  - ECO：`229dd819-4615-48b5-891d-ff9a1a830edf`
  - Version：`672a0e58-9025-40d2-9713-c34bd2421cc3`

执行命令：

```bash
PY=/usr/bin/python3 \
CLI=/tmp/yuantus_cli_compose.sh \
  bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Integrations health: OK (ok=False)
ALL CHECKS PASSED
```

## Run BOM-COMPARE-SCHEMA-20260113-2212（BOM Compare Field Contract + Schema）

- 时间：`2026-01-13 22:12:55 +0800`
- 脚本：`scripts/verify_bom_compare_fields.sh`
- 环境：`TENANCY=db-per-tenant-org`

```bash
bash scripts/verify_bom_compare_fields.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
ALL CHECKS PASSED
```

## Run S8-20260119-1455（S8 Ops Monitoring）

- 时间：`2026-01-19 14:55:23 +0800`
- 基地址：`http://127.0.0.1:7915`
- 脚本：`scripts/verify_ops_s8.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - `PYTHONPATH=/Users/huazhou/Downloads/Github/Yuantus-worktrees/main-codex-yuantus/src`
  - `YUANTUS_DATABASE_URL=sqlite:///yuantus_s8_meta.db`
  - `YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_s8_identity.db`
  - `YUANTUS_SCHEMA_MODE=create_all`
  - `YUANTUS_TENANCY_MODE=single`
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`
- 关键 ID：
  - Part：`df3311fa-d22a-4e5a-beb4-40a455190ff1`
  - File：`19d6ce9b-1c52-4b9d-a20e-6bb05ce79ae3`
  - ECO：`81e36bde-0383-4dd9-bb88-51c099b363b3`
  - Job：`7b638feb-3cda-40b1-ae04-26eff85a061a`

执行命令：

```bash
PYTHONPATH=/Users/huazhou/Downloads/Github/Yuantus-worktrees/main-codex-yuantus/src \
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_DATABASE_URL=sqlite:///yuantus_s8_meta.db \
YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_s8_identity.db \
DB_URL=sqlite:///yuantus_s8_meta.db \
IDENTITY_DB_URL=sqlite:///yuantus_s8_identity.db \
bash scripts/verify_ops_s8.sh http://127.0.0.1:7915 tenant-1 org-1
```

输出（摘要）：

```text
Quota monitoring: OK
Retention endpoints: OK
Audit prune endpoint: OK
Summary checks: OK
ALL CHECKS PASSED
```

## Run S8-20260119-1536（S8 Ops Monitoring / Compose MT）

- 时间：`2026-01-19 15:36:32 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_s8.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `S3=MinIO http://localhost:59000`
- 关键 ID：
  - Part：`74cf4a56-a57a-42b7-afdd-3692be1148bf`
  - File：`7733b044-870e-4188-8356-5b21925205ae`
  - ECO：`12a12094-7b4c-4a6e-933d-97867a9684fb`
  - Job：`2e85bda6-85b1-460e-8c65-2e5d1f295deb`

执行命令：

```bash
DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
bash scripts/verify_ops_s8.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
Quota monitoring: OK
Retention endpoints: OK
Audit prune endpoint: OK
Summary checks: OK
ALL CHECKS PASSED
```

## Run ALL-20260119-1554（Full Regression + S8）

- 时间：`2026-01-19 15:54:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`（`RUN_OPS_S8=1`）
- 日志：`/tmp/verify_all_s8.log`
- 结果：`PASS: 35  FAIL: 0  SKIP: 9`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `RUN_OPS_S8=1`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`

执行命令：

```bash
RUN_OPS_S8=1 \
DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
PASS: 35  FAIL: 0  SKIP: 9
ALL TESTS PASSED
```

## Run UI-20260119-1618（Product/BOM/Docs UI）

- 时间：`2026-01-19 16:18:50 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：
  - `scripts/verify_product_detail.sh`
  - `scripts/verify_product_ui.sh`
  - `scripts/verify_where_used_ui.sh`
  - `scripts/verify_bom_ui.sh`
  - `scripts/verify_docs_approval.sh`
  - `scripts/verify_docs_eco_ui.sh`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `CLI=/tmp/yuantus_cli_compose.sh`
  - `PY=/usr/bin/python3`

执行命令：

```bash
DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_bom_ui.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_docs_approval.sh http://127.0.0.1:7910 tenant-1 org-1

DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run ALL-20260119-1632（Full Regression + UI Agg）

- 时间：`2026-01-19 16:32:50 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`（`RUN_UI_AGG=1`）
- 日志：`/tmp/verify_all_ui.log`
- 结果：`PASS: 40  FAIL: 0  SKIP: 10`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `RUN_UI_AGG=1`
  - `RUN_OPS_S8=0`
  - `CLI=/tmp/yuantus_cli_compose.sh`
  - `PY=/usr/bin/python3`

执行命令：

```bash
RUN_UI_AGG=1 \
DOCKER_HOST=unix:///Users/huazhou/.docker/run/docker.sock \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_ui.log
```

输出（摘要）：

```text
PASS: 40  FAIL: 0  SKIP: 10
ALL TESTS PASSED
```

## Run S7-OPS-20260119-1954（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-19 19:54:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_hardening.sh`
- 日志：`/tmp/verify_ops_hardening_s7.log`
- 结果：`ALL CHECKS PASSED`
- 环境：
  - `TENANCY=db-per-tenant-org`
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`
  - `VERIFY_QUOTA_MONITORING=1`
  - `VERIFY_RETENTION=1`
  - `VERIFY_RETENTION_ENDPOINTS=1`
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `CLI=/tmp/yuantus_cli_compose.sh`
  - `PY=/usr/bin/python3`

执行命令：

```bash
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2 | tee /tmp/verify_ops_hardening_s7.log
```

输出（摘要）：

```text
Multi-Tenancy Verification Complete
ALL CHECKS PASSED

Audit Logs Verification Complete
ALL CHECKS PASSED

Ops Health Verification Complete
ALL CHECKS PASSED

Search Reindex Verification Complete
ALL CHECKS PASSED

Ops Hardening Verification Complete
ALL CHECKS PASSED
```

## Run CAD-CONNECTORS-CONFIG-20260119-2011

- 时间：`2026-01-19 20:11:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors_config.sh`
- 日志：`/tmp/verify_cad_connectors_config_s7.log`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run CAD-CONNECTORS-20260119-2013（含真实样本）

- 时间：`2026-01-19 20:13:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_connectors.sh`（`RUN_REAL=1`）
- 日志：`/tmp/verify_cad_connectors_s7.log`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
RUN_REAL=1 \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
bash scripts/verify_cad_connectors.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run CAD-EXTRACTOR-EXTERNAL-20260119-2017

- 时间：`2026-01-19 20:17:47 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_extractor_external.sh`
- 日志：`/tmp/verify_cad_extractor_external_s7.log`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
CAD_EXTRACTOR_SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
CAD_EXTRACTOR_ALLOW_EMPTY=1 \
CAD_EXTRACTOR_CAD_FORMAT=HAOCHEN \
CAD_EXTRACTOR_CONNECTOR_ID=haochencad \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run CAD-EXTRACTOR-SERVICE-20260119-2018

- 时间：`2026-01-19 20:18:49 +0800`
- 基地址：`http://127.0.0.1:8200`
- 脚本：`scripts/verify_cad_extractor_service.sh`
- 日志：`/tmp/verify_cad_extractor_service_s7.log`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
START_SERVICE=0 \
PY=/usr/bin/python3 \
bash scripts/verify_cad_extractor_service.sh
```

## Run CAD-SYNC-TEMPLATE-20260119-2019

- 时间：`2026-01-19 20:19:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_sync_template.sh`
- 日志：`/tmp/verify_cad_sync_template_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run CAD-AUTO-PART-20260119-2019

- 时间：`2026-01-19 20:19:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_auto_part.sh`
- 日志：`/tmp/verify_cad_auto_part_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run DOCS-S2-20260119-2020

- 时间：`2026-01-19 20:20:59 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_documents.sh`
- 日志：`/tmp/verify_documents_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run DOC-LIFECYCLE-20260119-2021

- 时间：`2026-01-19 20:21:45 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_document_lifecycle.sh`
- 日志：`/tmp/verify_document_lifecycle_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run DOCS-APPROVAL-20260119-2022

- 时间：`2026-01-19 20:22:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_docs_approval.sh`
- 日志：`/tmp/verify_docs_approval_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run DOCS-ECO-UI-20260119-2022

- 时间：`2026-01-19 20:22:44 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_docs_eco_ui.sh`
- 日志：`/tmp/verify_docs_eco_ui_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run VERSION-FILES-20260119-2023

- 时间：`2026-01-19 20:23:19 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_version_files.sh`
- 日志：`/tmp/verify_version_files_s7.log`
- 结果：`ALL CHECKS PASSED`

## Run OPS-HARDENING-20260119-2024

- 时间：`2026-01-19 20:24:11 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_ops_hardening.sh`
- 日志：`/tmp/verify_ops_hardening_stage4.log`
- 结果：`ALL CHECKS PASSED`

## Run ALL-20260119-2037（Full Regression + S7/S8/UI）

- 时间：`2026-01-19 20:37:20 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_all.sh`（`RUN_OPS_S8=1`, `RUN_UI_AGG=1`）
- 日志：`/tmp/verify_all_stage4_pass.log`
- 结果：`PASS: 41  FAIL: 0  SKIP: 10`
- 环境：
  - `DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
  - `YUANTUS_STORAGE_TYPE=s3`
  - `YUANTUS_S3_ENDPOINT_URL=http://localhost:59000`
  - `YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000`
  - `YUANTUS_S3_BUCKET_NAME=yuantus`
  - `YUANTUS_S3_ACCESS_KEY_ID=minioadmin`
  - `YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin`
  - `YUANTUS_CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200`

执行命令：

```bash
RUN_OPS_S8=1 RUN_UI_AGG=1 \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_stage4_pass.log
```

输出（摘要）：

```text
PASS: 41  FAIL: 0  SKIP: 10
ALL TESTS PASSED
```

## Run ALL-20260120-0902（Full Regression + Ops S8）

- 时间：`2026-01-20 09:05:47 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS: 35  FAIL: 0  SKIP: 16`

执行命令：

```bash
RUN_OPS_S8=1 \
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260120_0902.log
```

输出（摘要）：

```text
PASS: 35  FAIL: 0  SKIP: 16
ALL TESTS PASSED
```

## Run S7-20260120-0833（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-20 08:33:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 开关：`YUANTUS_QUOTA_MODE=enforce`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_PLATFORM_ADMIN_ENABLED=true`
- 结果：全部通过

执行命令：

```bash
CLI=/tmp/yuantus_cli_compose.sh \
PY=/usr/bin/python3 \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260121-103449（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-21 10:34:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_ops_hardening.sh`
- 报告：`docs/S7_MULTITENANCY_VERIFICATION_20260121_103449.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
VERIFY_QUOTA_MONITORING=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260121-110044（Tenant Provisioning）

- 时间：`2026-01-21 11:00:44 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 日志：`docs/S7_TENANT_PROVISIONING_20260121_110044.log`
- 报告：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260121_110044.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
PLATFORM_TENANT=platform \
PLATFORM_ORG=platform \
PLATFORM_USER=platform-admin \
PLATFORM_PASSWORD=platform-admin \
PLATFORM_USER_ID=9001 \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-0917（Ops Hardening / Multi-Tenancy Deep）

- 时间：`2026-01-23 09:17:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_ops_hardening.sh`
- 报告：`docs/S7_MULTITENANCY_VERIFICATION_20260123_0917.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
  bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-0918（Tenant Provisioning）

- 时间：`2026-01-23 09:18:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_tenant_provisioning.sh`
- 报告：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260123_0918.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-1107（S7 Deep Verification）

- 时间：`2026-01-23 11:07:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_s7.sh`
- 报告：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1107.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-1107（Tenant Provisioning）

- 时间：`2026-01-23 11:07:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_s7.sh`
- 报告：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260123_1107.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-1122（S7 Deep Verification）

- 时间：`2026-01-23 11:22:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_s7.sh`
- 报告：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1122.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/YuantusPLM/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/YuantusPLM/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run S7-20260123-1122（Tenant Provisioning）

- 时间：`2026-01-23 11:22:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`scripts/verify_s7.sh`
- 报告：`docs/S7_TENANT_PROVISIONING_VERIFICATION_20260123_1122.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=/Users/huazhou/Downloads/Github/YuantusPLM/.venv/bin/yuantus \
PY=/Users/huazhou/Downloads/Github/YuantusPLM/.venv/bin/python \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run REL-20260123-1307（Relationships as Items）

- 时间：`2026-01-23 13:07:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 模式：`db-per-tenant-org`
- 脚本：`verify_bom_tree` / `verify_bom_effectivity` / `verify_versions` / `verify_eco_advanced`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_20260123_1307.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
MODE=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_bom_effectivity.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
bash scripts/verify_versions.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run CAD-MESH-STATS-20260121-1339

- 时间：`2026-01-21 13:39:07 +0800`
- 基地址：`http://127.0.0.1:7910`
- 接口：`GET /api/v1/cad/files/{file_id}/mesh-stats`
- 报告：`docs/VERIFICATION_CAD_MESH_STATS_20260121_133907.md`
- 结果：`HTTP 200`，`stats.available=false`（无 metadata 时不再 404）

执行命令：

```bash
TOKEN=$(curl -s http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')

curl -s http://127.0.0.1:7910/api/v1/cad/files/630a312a-628f-40b7-b5cc-5f317536aa5e/mesh-stats \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' \
  -H 'x-org-id: org-1'
```

## Run CAD-PREVIEW-2D-20260121-1342

- 时间：`2026-01-21 13:42:47 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 报告：`docs/VERIFICATION_CAD_PREVIEW_2D_20260121_134247.md`
- 结果：`SKIP`（CAD ML Vision 未启动，HTTP 000000）

执行命令：

```bash
bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run CAD-PREVIEW-2D-20260121-1520

- 时间：`2026-01-21 15:20:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 报告：`docs/VERIFICATION_CAD_PREVIEW_2D_20260121_152035.md`
- 结果：`ALL CHECKS PASSED`（CAD ML 422 fallback，preview 302，mesh stats available=false）

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
CAD_ML_BASE_URL=http://localhost:8000 \
  bash scripts/verify_cad_preview_2d.sh
```

## Run CAD-PREVIEW-2D-20260121-1548

- 时间：`2026-01-21 15:48:00 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 报告：`docs/VERIFICATION_CAD_PREVIEW_2D_20260121_154800.md`
- 结果：`ALL CHECKS PASSED`（使用 ODA render 服务，DWG 渲染成功）

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
CAD_ML_BASE_URL=http://localhost:18002 \
CAD_ML_HEALTH_URL=http://localhost:18002/health \
  bash scripts/verify_cad_preview_2d.sh
```

## Run CAD-PREVIEW-2D-20260121-2055

- 时间：`2026-01-21 20:55:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_cad_preview_2d.sh`
- 报告：`docs/VERIFICATION_CAD_PREVIEW_2D_20260121_205535.md`
- 结果：`ALL CHECKS PASSED`（cad-ml render fallback enabled）

执行命令：

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
STORAGE_TYPE=s3 \
S3_ENDPOINT_URL='http://localhost:59000' \
S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
S3_BUCKET_NAME=yuantus \
S3_ACCESS_KEY_ID=minioadmin \
S3_SECRET_ACCESS_KEY=minioadmin \
CAD_ML_BASE_URL=http://localhost:8000 \
  bash scripts/verify_cad_preview_2d.sh
```

## Run BOM-API-STABILITY-20260122-1431

- 时间：`2026-01-22 14:31:47 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：BOM Compare / Where-Used / Substitutes
- 报告：`docs/VERIFICATION_BOM_API_STABILITY_20260122_143147.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_substitutes.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run VERSION-FILE-APPROVAL-20260122-1457

- 时间：`2026-01-22 14:57:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Version-file binding + ECO approval flow
- 报告：`docs/VERIFICATION_VERSION_FILE_APPROVAL_20260122_145709.md`
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_docs_approval.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run REL-WRITE-MON-20260123-1407

- 时间：`2026-01-23 14:07:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Deprecated relationship write monitor
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export YUANTUS_RELATIONSHIP_SIMULATE_ENABLED=true

TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"platform","org_id":"org-1","username":"platform-admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s "http://127.0.0.1:7910/api/v1/admin/relationship-writes" \
  -H "x-tenant-id: platform" -H "x-org-id: org-1" \
  -H "Authorization: Bearer $TOKEN"

curl -s -X POST "http://127.0.0.1:7910/api/v1/admin/relationship-writes/simulate?operation=insert" \
  -H "x-tenant-id: platform" -H "x-org-id: org-1" \
  -H "Authorization: Bearer $TOKEN"
```

## Run REL-MIGRATION-DRY-20260123-1424

- 时间：`2026-01-23 14:24:57 +0800`
- 范围：Relationship → Item 迁移 dry-run（db-per-tenant-org）
- 结果：`ALL CHECKS PASSED`（所有 tenant/org 的 meta_relationships 为空）

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus"

python3 scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --dry-run --update-item-types
python3 scripts/migrate_relationship_items.py --tenant tenant-1 --org org-2 --dry-run --update-item-types
python3 scripts/migrate_relationship_items.py --tenant tenant-2 --org org-1 --dry-run --update-item-types
```

## Run REL-PHASE3-20260123-1429

- 时间：`2026-01-23 14:29:06 +0800`
- 范围：Phase 3 非破坏性清理（禁用遗留桥接写入）
- 结果：`ALL CHECKS PASSED`

说明：
- `PartBOMBridge` 已禁用并返回明确错误，避免 legacy 写入路径。

## Run VERSION-FILE-BINDING-20260123-1447

- 时间：`2026-01-23 14:47:34 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：版本-文件绑定深化（版本文件编辑需 checkout）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run ECO-ADVANCED-20260123-1459

- 时间：`2026-01-23 14:59:41 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：ECO apply 文件同步验证（版本文件 → ItemFile）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

CLI=.venv/bin/yuantus PY=.venv/bin/python \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run REL-WRITE-WARN-20260123-1519

- 时间：`2026-01-23 15:19:15 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Deprecated relationship write 告警阈值（warn_threshold）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

# Seed platform admin identity
.venv/bin/yuantus seed-identity \
  --tenant platform --org platform \
  --username platform-admin --password platform-admin \
  --user-id 9001 --roles admin --superuser

# Login + validate warn threshold
PLATFORM_TOKEN="$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"platform","username":"platform-admin","password":"platform-admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"

curl -s "http://127.0.0.1:7910/api/v1/admin/relationship-writes?window_seconds=86400&recent_limit=20&warn_threshold=1" \
  -H "x-tenant-id: platform" \
  -H "Authorization: Bearer $PLATFORM_TOKEN"

curl -s -X POST "http://127.0.0.1:7910/api/v1/admin/relationship-writes/simulate?operation=insert&warn_threshold=1" \
  -H "x-tenant-id: platform" \
  -H "Authorization: Bearer $PLATFORM_TOKEN"
```

输出（节选）：

```json
{"window_seconds":86400,"blocked":0,"recent":[],"last_blocked_at":null,"warn_threshold":1,"warn":false}
{"window_seconds":86400,"blocked":1,"recent":[1769152735.3358703],"last_blocked_at":1769152735.3358703,"warn_threshold":1,"warn":true}
```

## Run S7-DEEP-20260123-1526

- 时间：`2026-01-23 15:26:28 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：S7 深度验证（多租户 + 配额 + 审计 + 健康 + 索引 + 平台管理员）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
CLI=.venv/bin/yuantus PY=.venv/bin/python \
MODE=db-per-tenant-org \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

## Run REL-MIGRATION-DRY-20260123-1536

- 时间：`2026-01-23 15:36:01 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship → Item 迁移 dry-run（db-per-tenant-org）
- 结果：`ALL CHECKS PASSED`（tenant-2/org-2 无表，已跳过）

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

PY=.venv/bin/python
for tenant in tenant-1 tenant-2; do
  for org in org-1 org-2; do
    echo "==> Dry-run $tenant / $org"
    $PY scripts/migrate_relationship_items.py --tenant "$tenant" --org "$org" --dry-run
  done
done
```

输出（节选）：

```text
==> Dry-run tenant-1 / org-1
Relationships: total=0 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 0
...
==> Dry-run tenant-2 / org-2
Skip migration: meta_relationships missing (tenant=tenant-2 org=org-2)
```

## Run REL-MIGRATION-DRY-20260123-1541

- 时间：`2026-01-23 15:41:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship → Item dry-run（tenant-2/org-2 补齐 schema 后）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-2__org-2 \
  .venv/bin/yuantus db upgrade

export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

PY=.venv/bin/python \
  python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --dry-run
```

输出（节选）：

```text
Relationships: total=0 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 0
```

## Run REL-MIGRATION-ACTUAL-REMAINING-20260123-1607

- 时间：`2026-01-23 16:07:09 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship → Item 实际迁移（tenant-1/org-2、tenant-2/org-1、tenant-2/org-2）
- 结果：`ALL CHECKS PASSED`

备份：

```bash
tmp/rel-migration-backup-tenant-1-org-2-codex-yuantus-20260123-160652.sql
tmp/rel-migration-backup-tenant-2-org-1-codex-yuantus-20260123-160652.sql
tmp/rel-migration-backup-tenant-2-org-2-codex-yuantus-20260123-160652.sql
```

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

PY=.venv/bin/python
python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-2
python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-1
python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2
```

输出（节选）：

```text
tenant-1/org-2: Relationships=0, Migrated=0
tenant-2/org-1: Relationships=0, Migrated=0
tenant-2/org-2: Relationships=0, Migrated=0
```

## Run BOM-COMPARE-FIELDS-20260123-1615

- 时间：`2026-01-23 16:15:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：BOM Compare 字段级对照验收（schema + diff payload）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
bash scripts/verify_bom_compare_fields.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run REL-MIGRATION-DRY-SEED-20260123-1548

- 时间：`2026-01-23 15:48:19 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship → Item dry-run（插入 1 条合成关系后验证）
- 结果：`ALL CHECKS PASSED`

执行步骤（摘要）：

```sql
-- tenant-2/org-2 DB: yuantus_mt_pg__tenant-2__org-2
INSERT meta_relationship_types (Part BOM)
INSERT meta_items (REL-TEST-A / REL-TEST-B)
INSERT meta_relationships (qty=2, uom=EA)
```

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

PY=.venv/bin/python \
  python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --dry-run
```

输出（节选）：

```text
Relationships: total=1 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 1
```

## Run REL-MIGRATION-ROLLBACK-20260123-1554

- 时间：`2026-01-23 15:54:36 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship → Item 备份 + 迁移 + 回滚演练（tenant-2/org-2）
- 结果：`ALL CHECKS PASSED`

备份：

```bash
BACKUP=tmp/rel-migration-backup-tenant-2-org-2-codex-yuantus-20260123-155303.sql
docker exec yuantus-postgres-1 pg_dump -U yuantus -d yuantus_mt_pg__tenant-2__org-2 > "$BACKUP"
```

迁移演练（合成关系）：

```sql
INSERT meta_relationship_types (Part BOM)
INSERT meta_items (REL-ROLLBACK2-A / REL-ROLLBACK2-B)
INSERT meta_relationships (qty=4, uom=EA)
```

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

PY=.venv/bin/python \
  python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2
```

输出（节选）：

```text
Relationships: total=1 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 1
```

回滚（清理测试数据）：

```sql
DELETE FROM meta_items WHERE id = '70b25077-a929-47df-b8c7-198ed1c9f708';
DELETE FROM meta_relationships WHERE id = '70b25077-a929-47df-b8c7-198ed1c9f708';
DELETE FROM meta_items WHERE id IN ('6a53c138-70dc-4c11-ad1b-21423bb780e4','4fe7cbbd-f66d-4e15-ac2e-5a13adaa14e8');
DELETE FROM meta_relationship_types WHERE id = 'Part BOM';
```

## Run REL-MIGRATION-ACTUAL-20260123-1601

- 时间：`2026-01-23 16:01:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship → Item 实际迁移（tenant-1/org-1）
- 结果：`ALL CHECKS PASSED`

备份：

```bash
BACKUP=tmp/rel-migration-backup-tenant-1-org-1-codex-yuantus-20260123-160107.sql
docker exec yuantus-postgres-1 pg_dump -U yuantus -d yuantus_mt_pg__tenant-1__org-1 > "$BACKUP"
```

执行命令：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
export YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

PY=.venv/bin/python \
  python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1
```

输出（节选）：

```text
Relationships: total=0 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 0
```

清理：

```sql
DELETE FROM meta_relationships WHERE id = 'd3ed5b60-dcc8-4032-9e36-2dd36527fca3';
DELETE FROM meta_items WHERE id IN ('69b675aa-f621-4d74-98de-0ad9469c4c79','9ec011cb-f139-418d-9c2f-641b4a006c25');
DELETE FROM meta_relationship_types WHERE id = 'Part BOM';
```

## Run ECO-ADVANCED-20260123-1727

- 时间：`2026-01-23 17:27:20 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：ECO Impact + BOM Redline + 批量审批（S4.2/S4.3 回归）
- 结果：`ALL CHECKS PASSED`

执行命令：

```bash
DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1" \
IDENTITY_DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg" \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run S7-20260123-1953（S7 Deep Verification）

- 时间：`2026-01-23 19:54:08 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：S7 深度验证（多租户 + 配额 + 审计 + 健康 + 索引 + 平台管理员）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1953.md`
- 日志：`docs/S7_MULTITENANCY_VERIFICATION_20260123_1953.log`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
AUDIT_RETENTION_DAYS=1 \
AUDIT_RETENTION_MAX_ROWS=10 \
AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 \
VERIFY_QUOTA_MONITORING=1 \
VERIFY_RETENTION=1 \
VERIFY_RETENTION_ENDPOINTS=1 \
CLI=.venv/bin/yuantus \
PY=.venv/bin/python \
  bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

输出（摘要）：

```text
ALL CHECKS PASSED
```

## Run REL-MIGRATION-20260123-2059

- 时间：`2026-01-23 20:59:28 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship -> Item 迁移（db-per-tenant-org 全组合）
- 结果：`ALL CHECKS PASSED`（无关系数据）
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_20260123_2059.md`
- 日志：`docs/RELATIONSHIP_ITEM_MIGRATION_20260123_205846.log`

执行命令（节选）：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --update-item-types
```

输出（节选）：

```text
Relationships: total=0 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 0
```

## Run REL-MIGRATION-DATA-20260123-2139

- 时间：`2026-01-23 21:39:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship -> Item 迁移（tenant-2/org-2 带关系数据）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_DATA_20260123_2139.md`
- 日志：`docs/RELATIONSHIP_ITEM_MIGRATION_DATA_20260123_213905.log`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --update-item-types
```

输出（节选）：

```text
Relationships: total=2 existing_items=0
Missing type=0 source=0 related=0
Migrated relationship items: 2
```

## Run REL-PHASE3-20260123-2155

- 时间：`2026-01-23 21:55:30 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：Relationship 只读兼容层写入阻断监控
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_20260123_2155.md`
- 日志：`docs/RELATIONSHIP_WRITE_BLOCKS_20260123_215530.log`

执行命令（节选）：

```bash
curl -s "http://127.0.0.1:7910/api/v1/admin/relationship-writes?window_seconds=86400&recent_limit=20&warn_threshold=1" \
  -H "Authorization: Bearer <platform_token>" -H "x-tenant-id: platform"

curl -s -X POST "http://127.0.0.1:7910/api/v1/admin/relationship-writes/simulate?operation=insert&warn_threshold=1" \
  -H "Authorization: Bearer <platform_token>" -H "x-tenant-id: platform"
```

输出（节选）：

```text
{\"window_seconds\":86400,\"blocked\":0,\"recent\":[],\"last_blocked_at\":null,\"warn_threshold\":1,\"warn\":false}
{\"window_seconds\":86400,\"blocked\":1,\"recent\":[1769176530.292545],\"last_blocked_at\":1769176530.292545,\"warn_threshold\":1,\"warn\":true}
```

## Run REL-PHASE3-CLEANUP-20260123-2203

- 时间：`2026-01-23 22:03:59 +0800`
- 范围：兼容层写入硬阻断（无环境变量开关）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_CLEANUP_20260123_2203.md`
- 日志：`docs/RELATIONSHIP_ITEM_PHASE3_CLEANUP_20260123_220359.log`

输出（节选）：

```text
BLOCKED: RuntimeError meta_relationships is deprecated for writes; use meta_items relationship items instead.
```

## Run REL-POST-CLEANUP-20260123-2208

- 时间：`2026-01-23 22:08:46 +0800`
- 基地址：`http://127.0.0.1:7910`
- 范围：BOM Tree + Where-Used + ECO Advanced（Phase 3 后最小回归）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_POST_CLEANUP_20260123_2208.md`
- 日志：`docs/VERIFY_BOM_TREE_20260123_220846.log` / `docs/VERIFY_WHERE_USED_20260123_220846.log` / `docs/VERIFY_ECO_ADVANCED_20260123_220846.log`

执行命令（节选）：

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1

DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run ALL-20260123-2217（Full Regression）

- 时间：`2026-01-23 22:17:08 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`ALL TESTS PASSED`（PASS 35 / FAIL 0 / SKIP 16）
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260123_2217.md`
- 日志：`docs/VERIFY_ALL_20260123_221708.log`

执行命令：

```bash
bash scripts/verify_all.sh
```

## Run REL-DRYRUN-20260123-2231

- 时间：`2026-01-23 22:31:25 +0800`
- 目标：`tenant-2/org-2`（db-per-tenant-org）
- 结果：`ALL CHECKS PASSED`（dry-run）
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_DRYRUN_20260123_2231.md`
- 日志：`docs/RELATIONSHIP_ITEM_DRYRUN_20260123_223124.log`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --dry-run
```

## Run REL-ACTUAL-20260123-2241

- 时间：`2026-01-23 22:41:49 +0800`
- 目标：`tenant-2/org-2`（db-per-tenant-org）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_ACTUAL_20260123_2241.md`
- 日志：`docs/RELATIONSHIP_ITEM_MIGRATION_ACTUAL_20260123_224147.log`
- 备份：`tmp/rel-migration-backups-codex-yuantus-20260123_224120/yuantus_mt_pg__tenant-2__org-2-codex-yuantus-20260123_224120.sql`

执行命令：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python scripts/migrate_relationship_items.py --tenant tenant-2 --org org-2 --update-item-types
```

## Run REL-BATCH-20260123-2256

- 时间：`2026-01-23 22:56:40 +0800`
- 目标：`tenant-1/org-1`, `tenant-1/org-2`, `tenant-2/org-1`
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_BATCH_20260123_2256.md`
- 备份：`tmp/rel-migration-backups-codex-yuantus-20260123_225618/`

日志：

```text
docs/RELATIONSHIP_ITEM_DRYRUN_tenant-1_org-1_20260123_225638.log
docs/RELATIONSHIP_ITEM_ACTUAL_tenant-1_org-1_20260123_225638.log
docs/RELATIONSHIP_ITEM_DRYRUN_tenant-1_org-2_20260123_225638.log
docs/RELATIONSHIP_ITEM_ACTUAL_tenant-1_org-2_20260123_225638.log
docs/RELATIONSHIP_ITEM_DRYRUN_tenant-2_org-1_20260123_225638.log
docs/RELATIONSHIP_ITEM_ACTUAL_tenant-2_org-1_20260123_225638.log
```

## Run REL-SPOTCHECK-20260123-2312

- 时间：`2026-01-23 23:12:42 +0800`
- 范围：BOM Tree + ECO Advanced spot check
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_SPOTCHECK_20260123_2312.md`
- 日志：`docs/VERIFY_SPOT_BOM_WHERE_20260123_231242.log`, `docs/VERIFY_SPOT_ECO_ADV_20260123_231242.log`

执行命令（节选）：

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1

DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run UI-AGG-20260123-2342

- 时间：`2026-01-23 23:42:09 +0800`
- 范围：Product Detail / Product Summary / Where-Used UI / BOM UI / Docs Approval / Docs ECO Summary
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_UI_AGG_20260123_2342.md`
- 日志：`docs/VERIFY_UI_PRODUCT_DETAIL_20260123_234209.log`, `docs/VERIFY_UI_PRODUCT_UI_20260123_234209.log`, `docs/VERIFY_UI_WHERE_USED_20260123_234209.log`, `docs/VERIFY_UI_BOM_20260123_234209.log`, `docs/VERIFY_UI_DOCS_APPROVAL_20260123_234209.log`, `docs/VERIFY_UI_DOCS_ECO_20260123_234209.log`

执行命令（节选）：

```bash
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_bom_ui.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_docs_approval.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Run REL-PHASE2-20260124-0051

- 时间：`2026-01-24 00:51 +0800`
- 范围：AML expand 关系类型回退 ItemType（无 RelationshipType）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE2_20260124_0051.md`
- 日志：`docs/VERIFY_REL_ITEMTYPE_EXPAND_20260124_0051.log`

执行命令（节选）：

```bash
scripts/verify_relationship_itemtype_expand.sh | tee docs/VERIFY_REL_ITEMTYPE_EXPAND_20260124_0051.log
```

## Run REL-PHASE2-DRYRUN-20260124-1152

- 时间：`2026-01-24 11:52 +0800`
- 范围：relationship item 迁移 dry-run（tenant-1/org-1）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152.md`
- 日志：`docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152.log`

执行命令（节选）：

```bash
PYTHONPATH=src .venv/bin/python scripts/migrate_relationship_items.py \
  --tenant tenant-1 --org org-1 --dry-run | tee docs/RELATIONSHIP_ITEM_PHASE2_DRYRUN_20260124_1152.log
```

## Run REL-PHASE3-SEEDER-20260124-1429

- 时间：`2026-01-24 14:29 +0800`
- 范围：RelationshipType legacy 种子开关验证
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_SEEDER_20260124_1429.md`
- 日志：`docs/VERIFY_RELATIONSHIP_TYPE_SEEDING_20260124_1429.log`

执行命令（节选）：

```bash
scripts/verify_relationship_type_seeding.sh | tee docs/VERIFY_RELATIONSHIP_TYPE_SEEDING_20260124_1429.log
```

## Run REL-PHASE3-USAGE-20260124-1502

- 时间：`2026-01-24 15:02 +0800`
- 范围：legacy RelationshipType usage 报告验证
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_USAGE_20260124_1502.md`
- 日志：`docs/VERIFY_RELATIONSHIP_LEGACY_USAGE_20260124_1502.log`

执行命令（节选）：

```bash
scripts/verify_relationship_legacy_usage.sh | tee docs/VERIFY_RELATIONSHIP_LEGACY_USAGE_20260124_1502.log
```

## Run WHERE-USED-SCHEMA-20260124-2120

- 时间：`2026-01-24 21:20 +0800`
- 范围：where-used 行字段 schema 输出验证
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_WHERE_USED_SCHEMA_20260124_2120.md`
- 日志：`docs/VERIFY_WHERE_USED_SCHEMA_20260124_2120.log`

执行命令（节选）：

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_where_used_schema.sh \
  http://127.0.0.1:7910 tenant-1 org-1 | tee docs/VERIFY_WHERE_USED_SCHEMA_20260124_2120.log
```

## Run LOCAL-REGRESSION-20260124-2140

- 时间：`2026-01-24 21:40 +0800`
- 范围：TestClient 本地回归集合
- 结果：`PASS=7, FAIL=0, SKIP=0`
- 报告：`docs/VERIFICATION_LOCAL_REGRESSION_20260124_2140.md`
- 日志：`docs/VERIFY_ALL_LOCAL_20260124_2140.log`

执行命令（节选）：

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_all_local.sh \
  http://127.0.0.1:7910 tenant-1 org-1 | tee docs/VERIFY_ALL_LOCAL_20260124_2140.log
```

## Run WHERE-USED-SCHEMA-HTTP-20260124-2236

- 时间：`2026-01-24 22:36 +0800`
- 范围：where-used 行字段 schema（HTTP）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_WHERE_USED_SCHEMA_HTTP_20260124_223656.md`
- 日志：`docs/VERIFY_WHERE_USED_SCHEMA_HTTP_20260124_223656.log`

执行命令（节选）：

```bash
bash scripts/verify_where_used_schema.sh \
  http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_WHERE_USED_SCHEMA_HTTP_20260124_223656.log
```

## Run FULL-REGRESSION-20260124-2234

- 时间：`2026-01-24 22:34 +0800`
- 范围：全量回归（HTTP）
- 结果：`PASS=35, FAIL=0, SKIP=17`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260124_223403.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260124_223403.log`

执行命令（节选）：

```bash
bash scripts/verify_all.sh \
  http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_223403.log
```

## Run FULL-REGRESSION-20260124-2244

- 时间：`2026-01-24 22:44 +0800`
- 范围：全量回归（HTTP，含 UI + Ops + Tenant Provisioning）
- 结果：`PASS=44, FAIL=0, SKIP=8`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260124_224416.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260124_224416.log`

执行命令（节选）：

```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_224416.log
```

## Run FULL-REGRESSION-20260124-2255

- 时间：`2026-01-24 22:55 +0800`
- 范围：全量回归（HTTP，含 CAD 实样 + 连接器覆盖）
- 结果：`PASS=51, FAIL=0, SKIP=1`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260124_225535.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260124_225535.log`

执行命令（节选）：

```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
RUN_CAD_REAL_CONNECTORS_2D=1 RUN_CAD_CONNECTOR_COVERAGE_2D=1 RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 RUN_CAD_EXTRACTOR_EXTERNAL=1 RUN_CAD_EXTRACTOR_SERVICE=1 RUN_CAD_REAL_SAMPLES=1 \
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
CAD_CONNECTOR_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸" \
CAD_CONNECTOR_COVERAGE_MAX_FILES=50 \
CAD_EXTRACTOR_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg" \
CAD_SAMPLE_DWG="/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg" \
CAD_SAMPLE_STEP="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp" \
CAD_SAMPLE_PRT="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt" \
CAD_REAL_FORCE_UNIQUE=1 CAD_EXTRACTOR_ALLOW_EMPTY=1 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_225535.log
```

## Run CAD-PREVIEW-2D-20260124-2305

- 时间：`2026-01-24 23:05 +0800`
- 范围：CAD 2D 预览（ML 端点 8000）
- 结果：`ALL CHECKS PASSED`（mesh stats 可选项为 skip）
- 报告：`docs/VERIFICATION_CAD_PREVIEW_2D_20260124_230504.md`
- 日志：`docs/VERIFY_CAD_PREVIEW_2D_20260124_230504.log`

执行命令（节选）：

```bash
CAD_ML_BASE_URL=http://127.0.0.1:8000 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus" \
DB_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}" \
IDENTITY_DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg" \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_CAD_PREVIEW_2D_20260124_230504.log
```

## Run CAD-OCR-TITLEBLOCK-20260124-2305

- 时间：`2026-01-24 23:05 +0800`
- 范围：CAD OCR 标题栏解析（ML 端点 8000）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CAD_OCR_TITLEBLOCK_20260124_230542.md`
- 日志：`docs/VERIFY_CAD_OCR_TITLEBLOCK_20260124_230542.log`

执行命令（节选）：

```bash
CAD_ML_BASE_URL=http://127.0.0.1:8000 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus" \
DB_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}" \
IDENTITY_DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg" \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_CAD_OCR_TITLEBLOCK_20260124_230542.log
```

## Run FULL-REGRESSION-20260124-2311

- 时间：`2026-01-24 23:11 +0800`
- 范围：全量回归（HTTP，含 CAD ML 端点 + 实样 + 连接器覆盖）
- 结果：`PASS=51, FAIL=0, SKIP=1`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260124_2311.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260124_230935.log`

执行命令（节选）：

```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
RUN_CAD_REAL_CONNECTORS_2D=1 RUN_CAD_CONNECTOR_COVERAGE_2D=1 RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 RUN_CAD_EXTRACTOR_EXTERNAL=1 RUN_CAD_EXTRACTOR_SERVICE=1 RUN_CAD_REAL_SAMPLES=1 \
CAD_ML_BASE_URL=http://127.0.0.1:8000 \
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
CAD_CONNECTOR_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸" \
CAD_CONNECTOR_COVERAGE_MAX_FILES=50 \
CAD_EXTRACTOR_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg" \
CAD_SAMPLE_DWG="/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg" \
CAD_SAMPLE_STEP="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp" \
CAD_SAMPLE_PRT="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt" \
CAD_REAL_FORCE_UNIQUE=1 CAD_EXTRACTOR_ALLOW_EMPTY=1 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_230935.log
```

## Run FULL-REGRESSION-20260124-2338

- 时间：`2026-01-24 23:38 +0800`
- 范围：全量回归（HTTP，含 CADGF 在线预览 + CAD ML 端点 + 实样 + 连接器覆盖）
- 结果：`PASS=52, FAIL=0, SKIP=0`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260124_2338.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260124_233804.log`

执行命令（节选）：

```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
RUN_CAD_REAL_CONNECTORS_2D=1 RUN_CAD_CONNECTOR_COVERAGE_2D=1 RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 RUN_CAD_EXTRACTOR_EXTERNAL=1 RUN_CAD_EXTRACTOR_SERVICE=1 RUN_CAD_REAL_SAMPLES=1 \
RUN_CADGF_PREVIEW_ONLINE=1 CADGF_SYNC_GEOMETRY=1 \
CADGF_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf" \
CAD_ML_BASE_URL=http://127.0.0.1:8000 \
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
CAD_CONNECTOR_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸" \
CAD_CONNECTOR_COVERAGE_MAX_FILES=50 \
CAD_EXTRACTOR_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg" \
CAD_SAMPLE_DWG="/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg" \
CAD_SAMPLE_STEP="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp" \
CAD_SAMPLE_PRT="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt" \
CAD_REAL_FORCE_UNIQUE=1 CAD_EXTRACTOR_ALLOW_EMPTY=1 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus" \
YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}" \
YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg" \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion" \
YUANTUS_CADGF_CONVERT_CLI="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli" \
YUANTUS_CADGF_DXF_PLUGIN_PATH="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib" \
YUANTUS_CADGF_DEFAULT_EMIT="json,gltf,meta" \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260124_233804.log
```

## Run CADGF-PREVIEW-ONLINE-20260125-1234

- 时间：`2026-01-25 12:34 +0800`
- 范围：CADGF 在线预览（router 127.0.0.1:9000）
- 结果：`login_ok=yes, upload_ok=yes, conversion_ok=yes, viewer_load=yes`
- 报告：`docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260125_1234.md`
- 日志：`docs/VERIFY_CADGF_PREVIEW_ONLINE_20260125_123457.log`

## Run FULL-REGRESSION-20260125-1241

- 时间：`2026-01-25 12:41 +0800`
- 范围：全量回归（HTTP，含 CADGF 在线预览 + CAD ML 端点 + 实样 + 连接器覆盖）
- 结果：`PASS=52, FAIL=0, SKIP=0`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260125_1241.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260125_124121.log`

## Run RELATIONSHIP-ITEM-ADAPTER-20260125-1310

- 时间：`2026-01-25 13:10 +0800`
- 范围：Relationship 适配层（ItemType 优先）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_ADAPTER_20260125_1310.md`
- 日志：`docs/VERIFY_RUN_H_20260125_1310.log`

## Run CADGF-PREVIEW-ONLINE-20260125-2121

- 时间：`2026-01-25 21:21 +0800`
- 范围：CADGF 在线预览（DXF sample + 本地 router）
- 结果：`login_ok=yes, upload_ok=yes, conversion_ok=yes, viewer_load=yes, manifest_rewrite=yes`
- 报告：`docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260125_2121.md`

## Run CADGF-PREVIEW-ONLINE-20260125-2133

- 时间：`2026-01-25 21:33 +0800`
- 范围：CADGF 在线预览（DWG sample + host worker + 本地 router）
- 结果：`login_ok=yes, upload_ok=yes, conversion_ok=yes, viewer_load=yes, manifest_rewrite=yes`
- 报告：`docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260125_2133.md`

## Run CADGF-ROUTER-LAUNCHD-20260125-2150

- 时间：`2026-01-25 21:50 +0800`
- 范围：CADGF router launchd 常驻
- 结果：`health=ok`
- 设计：`docs/DESIGN_CADGF_ROUTER_LAUNCHD_20260125.md`
- 报告：`docs/VERIFICATION_CADGF_ROUTER_LAUNCHD_20260125_2150.md`

## Run CADGF-PREVIEW-ONLINE-20260125-2210

- 时间：`2026-01-25 22:10 +0800`
- 范围：CADGF 在线预览（DWG sample + launchd router + host worker）
- 结果：`login_ok=yes, upload_ok=yes, conversion_ok=yes, viewer_load=yes, manifest_rewrite=yes`
- 报告：`docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260125_2210.md`

## Run FULL-REGRESSION-20260125-2248

- 时间：`2026-01-25 22:48 +0800`
- 范围：全量回归（含 CADGF 在线预览）
- 结果：`PASS=36, FAIL=0, SKIP=16`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260125_2248.md`
- 日志：`docs/VERIFY_ALL_HTTP_20260125_2245.log`

## Run S7-DEEP-20260125-2302

- 时间：`2026-01-25 23:02 +0800`
- 范围：S7 深度验证（多租户 + 配额 + 审计 + Ops + 搜索 + 租户开通）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_S7_DEEP_VERIFICATION_20260125.md`
- 报告：`docs/VERIFICATION_S7_DEEP_20260125_2302.md`
- 日志：`docs/VERIFY_S7_20260125_2302.log`

## Run RELATIONSHIP-ITEM-MIGRATION-PHASE2-20260126-2326

- 时间：`2026-01-26 23:26 +0800`
- 范围：Relationship → Item Phase 2 迁移（db-per-tenant-org）
- 结果：`ALL CHECKS PASSED (no relationships to migrate)`
- 设计：`docs/DESIGN_RELATIONSHIP_ITEM_MIGRATION_PHASE2_20260126.md`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_MIGRATION_PHASE2_20260126_2326.md`
- 日志：`docs/VERIFY_REL_ITEM_MIGRATION_DRYRUN_20260126_2325.log`, `docs/VERIFY_REL_ITEM_MIGRATION_APPLY_20260126_2326.log`

## Run RELATIONSHIP-ITEM-MIGRATION-PHASE2-WITH-DATA-20260126-2334

- 时间：`2026-01-26 23:34 +0800`
- 范围：Relationship → Item Phase 2 迁移（含 legacy 数据）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_RELATIONSHIP_ITEM_MIGRATION_PHASE2_WITH_DATA_20260126.md`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_MIGRATION_PHASE2_WITH_DATA_20260126_2334.md`
- 日志：`docs/VERIFY_REL_ITEM_MIGRATION_DRYRUN_WITH_DATA_20260126_2334.log`, `docs/VERIFY_REL_ITEM_MIGRATION_APPLY_WITH_DATA_20260126_2334.log`

## Run UI-AGG-20260127-2352

- 时间：`2026-01-27 23:52 +0800`
- 范围：UI 聚合验证（product detail / BOM summary / where-used / docs approval / ECO summary）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_UI_AGG_20260127_2352.md`

## Run FULL-REGRESSION-20260128-0821

- 时间：`2026-01-28 08:23 +0800`
- 范围：全量回归（HTTP，RUN_UI_AGG=1）
- 结果：`PASS=42, FAIL=0, SKIP=10`
- 日志：`docs/VERIFY_ALL_HTTP_20260128_082158.log`

## Run FULL-REGRESSION-20260128-0843

- 时间：`2026-01-28 08:43 +0800`
- 范围：全量回归（HTTP，RUN_UI_AGG=1，RUN_CAD_REAL_SAMPLES=1，RUN_CADGF_PREVIEW_ONLINE=1）
- 结果：`PASS=44, FAIL=0, SKIP=8`
- 日志：`docs/VERIFY_ALL_HTTP_20260128_084149.log`

## Run CAD-REAL-CONNECTORS-2D-20260128-0849

- 时间：`2026-01-28 08:49 +0800`
- 范围：CAD 2D 实样连接器（Haochen/Zhongwang）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CAD_CONNECTORS_REAL_2D_20260128_0849.md`

## Run CAD-CONNECTOR-COVERAGE-2D-20260128-0849

- 时间：`2026-01-28 08:49 +0800`
- 范围：CAD 2D 连接器覆盖率（离线，DWG，max_files=50）
- 结果：`DONE`
- 报告：`docs/VERIFICATION_CAD_CONNECTOR_COVERAGE_2D_20260128_0849.md`
- 覆盖：`docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`, `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`

## Run CAD-AUTO-PART-20260128-1110

- 时间：`2026-01-28 11:10 +0800`
- 范围：CAD Auto Part
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CAD_AUTO_PART_20260128_1110.md`

## Run CAD-EXTRACTOR-SERVICE-20260128-1113

- 时间：`2026-01-28 11:13 +0800`
- 范围：CAD Extractor Service
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CAD_EXTRACTOR_SERVICE_20260128_1113.md`

## Run OPS-S8-20260128-1118

- 时间：`2026-01-28 11:18 +0800`
- 范围：S8 Ops Monitoring（quota + audit retention + reports summary）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_OPS_S8_20260128_1118.md`

## Run CAD-EXTRACTOR-STUB-20260128-1140

- 时间：`2026-01-28 11:40 +0800`
- 范围：CAD Extractor Stub
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CAD_EXTRACTOR_STUB_20260128_1140.md`

## Run CAD-EXTRACTOR-EXTERNAL-20260128-1142

- 时间：`2026-01-28 11:42 +0800`
- 范围：CAD Extractor External
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CAD_EXTRACTOR_EXTERNAL_20260128_1142.md`

## Run RELATIONSHIP-ITEM-ADAPTER-20260128-1201

- 时间：`2026-01-28 12:01 +0800`
- 范围：Relationship → Item Phase 1 适配层（seeding / expand / legacy usage）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_ADAPTER_20260128_1201.md`

## Run RELATIONSHIP-ITEM-MIGRATION-DRYRUN-20260128-1410

- 时间：`2026-01-28 14:10 +0800`
- 范围：Relationship → Item Phase 2 迁移（dry-run, db-per-tenant-org）
- 结果：`ALL CHECKS PASSED (no relationships to migrate)`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_MIGRATION_DRYRUN_20260128_1410.md`

## Run RELATIONSHIP-ITEM-MIGRATION-APPLY-20260128-1426

- 时间：`2026-01-28 14:26 +0800`
- 范围：Relationship → Item Phase 2 迁移（apply, db-per-tenant-org）
- 结果：`ALL CHECKS PASSED (no relationships to migrate)`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_MIGRATION_APPLY_20260128_1426.md`

## Run RELATIONSHIP-ITEM-PHASE3-20260128-1432

- 时间：`2026-01-28 14:32 +0800`
- 范围：Phase 3（relationship-writes 监控 / simulate / legacy usage / 强制只读）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE3_20260128_1432.md`

## Run RELATIONSHIP-ITEM-PHASE4-20260128-1537

- 时间：`2026-01-28 15:37 +0800`
- 范围：Phase 4（legacy usage 文案与只读告警输出）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE4_20260128_1537.md`

## Run RELATIONSHIP-ITEM-PHASE5-20260128-1545

- 时间：`2026-01-28 15:45 +0800`
- 范围：Phase 5（legacy 关系类型仅在显式开启时可用）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE5_20260128_1545.md`

## Run RELATIONSHIP-ITEM-PHASE6-20260128-1603

- 时间：`2026-01-28 16:03 +0800`
- 范围：Phase 6（运行时移除 legacy RelationshipType 回退）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE6_20260128_1603.md`

## Run RELATIONSHIP-ITEM-PHASE7-20260128-1617

- 时间：`2026-01-28 16:17 +0800`
- 范围：Phase 7（admin legacy usage 改为 raw SQL，移除 runtime ORM 依赖）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE7_20260128_1617.md`

## Run RELATIONSHIP-ITEM-PHASE8-20260128-1714

- 时间：`2026-01-28 17:14 +0800`
- 范围：Phase 8（legacy 关系模型软迁移，保持 import 兼容）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE8_20260128_1714.md`

## Run RELATIONSHIP-ITEM-PHASE9-20260128-1747

- 时间：`2026-01-28 17:47 +0800`
- 范围：Phase 9（内部模块改为显式 legacy_models 引用）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE9_20260128_1747.md`

## Run RELATIONSHIP-ITEM-PHASE10-20260128-1754

- 时间：`2026-01-28 17:54 +0800`
- 范围：Phase 10（deprecated import 警告 + 内部引用守护）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE10_20260128_1754.md`

## Run RELATIONSHIP-ITEM-PHASE11-20260128-1801

- 时间：`2026-01-28 18:01 +0800`
- 范围：Phase 11（文档清理：RelationshipType 标记为 legacy）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_PHASE11_20260128_1801.md`

## Run FULL-REGRESSION-20260128-1809

- 时间：`2026-01-28 18:09 +0800`
- 范围：全量回归（run_full_regression.sh）
- 结果：`ALL TESTS PASSED (PASS=44, FAIL=0, SKIP=8)`
- 报告：`docs/VERIFICATION_FULL_REGRESSION_20260128_1809.md`

## Run UI-AGG-20260128-2052

- 时间：`2026-01-28 20:52 +0800`
- 范围：UI 聚合回归（RUN_UI_AGG=1）
- 结果：`ALL TESTS PASSED (PASS=42, FAIL=0, SKIP=10)`
- 报告：`docs/VERIFICATION_UI_AGG_20260128_2052.md`

## Run CADGF-PREVIEW-ONLINE-20260128-2101

- 时间：`2026-01-28 21:01 +0800`
- 范围：CADGF 在线预览（router + preview）
- 结果：`SKIP (Missing CADGF_ROOT / router artifacts)`
- 报告：`docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260128_2101.md`

## Run CADGF-PREVIEW-ONLINE-20260128-2114

- 时间：`2026-01-28 21:14 +0800`
- 范围：CADGF 在线预览（router + preview）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260128_2114.md`

## Run S12-CONFIG-VARIANTS-20260128-2303

- 时间：`2026-01-28 23:03 +0800`
- 范围：S12 Configuration/Variant BOM（选项集 + BOM config_condition 过滤）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CONFIG_VARIANTS_20260128_2303.md`

## Run ALL-20260128-2318（一键回归：verify_all.sh，含 S12 Config Variants）

- 时间：`2026-01-28 23:18 +0800`
- 范围：全量回归（RUN_CONFIG_VARIANTS=1）
- 结果：`ALL TESTS PASSED (PASS=37, FAIL=0, SKIP=16)`
- 报告：`docs/VERIFICATION_RUN_ALL_S12_CONFIG_VARIANTS_20260128_2318.md`

## Run H-20260128-2334（发布前快速回归）

- 时间：`2026-01-28 23:34 +0800`
- 范围：Run H 核心功能回归（Health → AML → File → BOM → ECO → Versions → Plugins）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_RUN_H_20260128_2334.md`

## Run PROD-DETAIL-ALIASES-20260129-0918

- 时间：`2026-01-29 09:18 +0800`
- 范围：Product Detail alias fields（item_type/status/created_on）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_PRODUCT_DETAIL_ALIASES_20260129_0918.md`

## Run UI-AGG-20260129-0924（产品详情/UI 聚合回归）

- 时间：`2026-01-29 09:24 +0800`
- 范围：Product Detail / BOM Summary / Where-Used / Docs + ECO Summary
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_UI_AGG_20260129_0924.md`

## Run PROD-DETAIL-CAD-20260129-0936

- 时间：`2026-01-29 09:36 +0800`
- 范围：Product Detail 文件 CAD 摘要字段与预览链接
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_PRODUCT_DETAIL_CAD_SUMMARY_20260129_0936.md`

## Run ALL-UI-20260129-0946（一键回归：verify_all.sh，RUN_UI_AGG=1）

- 时间：`2026-01-29 09:46 +0800`
- 范围：全量回归 + UI 聚合
- 结果：`ALL TESTS PASSED (PASS=42, FAIL=0, SKIP=11)`
- 报告：`docs/VERIFICATION_UI_AGG_RUN_ALL_20260129_0946.md`

## Run ALL-UI-CONFIG-20260129-1007（一键回归：verify_all.sh，RUN_UI_AGG=1 + RUN_CONFIG_VARIANTS=1）

- 时间：`2026-01-29 10:07 +0800`
- 范围：全量回归 + UI 聚合 + 配置变体
- 结果：`ALL TESTS PASSED (PASS=43, FAIL=0, SKIP=10)`
- 报告：`docs/VERIFICATION_RUN_ALL_UI_CONFIG_20260129_1007.md`

## Run S12-CONFIG-VARIANTS-EXT-20260129-1149

- 时间：`2026-01-29 11:49 +0800`
- 范围：S12 配置变体条件表达增强（op/exists/missing/简写表达式）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CONFIG_VARIANTS_EXT_20260129_1149.md`

## Run S12-CONFIG-VARIANTS-EXT-DOCKER-20260129-1152

- 时间：`2026-01-29 11:52 +0800`
- 范围：S12 配置变体条件表达增强（Docker 7910）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_CONFIG_VARIANTS_EXT_DOCKER_20260129_1152.md`

## Run ALL-CONFIG-VARIANTS-20260129-1152（一键回归：verify_all.sh，RUN_CONFIG_VARIANTS=1）

- 时间：`2026-01-29 11:52 +0800`
- 范围：全量回归 + 配置变体
- 结果：`ALL TESTS PASSED (PASS=37, FAIL=0, SKIP=16)`
- 报告：`docs/VERIFICATION_RUN_ALL_CONFIG_VARIANTS_20260129_1152.md`

## Run PROD-DETAIL-FILE-ALIASES-20260129-1224

- 时间：`2026-01-29 12:24 +0800`
- 范围：产品详情文件别名字段（name/type/role/mime/size/version）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_PRODUCT_DETAIL_FILE_ALIASES_20260129_1224.md`

## Run DOCS-ECO-UI-ITEMS-20260129-1229

- 时间：`2026-01-29 12:29 +0800`
- 范围：产品详情文档/ECO 摘要 items 列表
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_DOCS_ECO_UI_ITEMS_20260129_1229.md`

## Run BOM-UI-ALIASES-20260129-1245

- 时间：`2026-01-29 12:45 +0800`
- 范围：BOM UI 别名字段（where-used/compare/substitutes）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_BOM_UI_ALIAS_FIELDS_20260129_1245.md`

## Run ALL-UI-CONFIG-20260129-1322（一键回归：verify_all.sh，RUN_UI_AGG=1 + RUN_CONFIG_VARIANTS=1）

- 时间：`2026-01-29 13:22 +0800`
- 范围：全量回归 + UI 聚合 + 配置变体
- 结果：`ALL TESTS PASSED (PASS=43, FAIL=0, SKIP=10)`
- 报告：`docs/VERIFICATION_RUN_ALL_UI_CONFIG_20260129_1322.md`

## Run UI-INTEGRATION-20260129-1329

- 时间：`2026-01-29 13:29 +0800`
- 范围：UI 端联调验证（产品详情/where-used/BOM/文档审批）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_UI_INTEGRATION_20260129_1329.md`

## Run RELEASE-v0.1.3-20260129

- 时间：`2026-01-29`
- 范围：v0.1.3 发布验证基线（引用全量回归）
- 结果：`PASS`
- 报告：`docs/VERIFICATION_RELEASE_v0.1.3_20260129.md`

## Run S7-DEEP-20260129-1504（多租户深度验证）

- 时间：`2026-01-29 15:04 +0800`
- 范围：S7 深度验证（多租户隔离 + 配额 + 审计 + Ops + 搜索 + 租户开通）
- 结果：`ALL CHECKS PASSED`（Quota/Audit/Platform Admin 条件为 SKIP）
- 报告：`docs/VERIFICATION_S7_DEEP_20260129_1504.md`

## Run S7-DEEP-20260129-1646（多租户深度验证，全量）

- 时间：`2026-01-29 16:46 +0800`
- 范围：S7 深度验证（多租户隔离 + 配额 + 审计 + Ops + 搜索 + 租户开通）
- 结果：`ALL CHECKS PASSED`
- 报告：`docs/VERIFICATION_S7_DEEP_20260129_1646.md`

## Run ALL-UI-CONFIG-S7-20260129-1655（全量回归 + UI + 配置变体 + S7）

- 时间：`2026-01-29 16:55 +0800`
- 范围：全量回归（RUN_UI_AGG=1 + RUN_CONFIG_VARIANTS=1 + RUN_TENANT_PROVISIONING=1）
- 结果：`ALL TESTS PASSED (PASS=44, FAIL=0, SKIP=9)`
- 报告：`docs/VERIFICATION_RUN_ALL_UI_CONFIG_S7_20260129_1655.md`
- 说明：开发总结 `docs/DEVELOPMENT_REPORT_S7_FULL_REGRESSION_20260129.md`

## Run REL-ITEM-UNIFY-20260129-1733（关系即 Item 统一验证）

- 时间：`2026-01-29 17:33 +0800`
- 范围：Relationship ItemType expand + legacy RelationshipType seeding
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_RELATIONSHIP_ITEM_UNIFY_20260129.md`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_UNIFY_20260129_1733.md`

## Run REL-ITEM-MIGRATION-DRYRUN-20260129-1806（关系迁移干跑）

- 时间：`2026-01-29 18:06 +0800`
- 范围：多租户库 legacy `meta_relationships` 统计（dry-run）
- 结果：`NO MIGRATION NEEDED`（所有 tenant/org 为 0 或表缺失）
- 设计：`docs/DESIGN_RELATIONSHIP_ITEM_MIGRATION_DRYRUN_20260129.md`
- 报告：`docs/VERIFICATION_RELATIONSHIP_ITEM_MIGRATION_20260129_1806.md`

## Run OPS-S8-20260129-2037

- 时间：`2026-01-29 20:37 +0800`
- 范围：S8 Ops Monitoring（quota + audit retention + reports summary）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_OPS_S8_20260129.md`
- 报告：`docs/VERIFICATION_OPS_S8_20260129_2037.md`

## Run ALL-UI-CONFIG-S7-S8-20260129-2046（全量回归 + S7 + S8）

- 时间：`2026-01-29 20:46 +0800`
- 范围：全量回归（RUN_UI_AGG=1 + RUN_CONFIG_VARIANTS=1 + RUN_TENANT_PROVISIONING=1 + RUN_OPS_S8=1）
- 结果：`ALL TESTS PASSED (PASS=45, FAIL=0, SKIP=8)`
- 报告：`docs/VERIFICATION_RUN_ALL_UI_CONFIG_S7_S8_20260129_2046.md`
- 说明：开发总结 `docs/DEVELOPMENT_REPORT_FULL_REGRESSION_S7_S8_20260129.md`

## Run CAD-CONNECTOR-MATRIX-20260129-2116

- 时间：`2026-01-29 21:16 +0800`
- 范围：CAD 连接器能力矩阵（/api/v1/cad/connectors）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_CAD_CONNECTOR_MATRIX_20260129.md`
- 报告：`docs/VERIFICATION_CAD_CONNECTOR_MATRIX_20260129_2116.md`

## Run PLUGIN-FRAMEWORK-20260129-2121

- 时间：`2026-01-29 21:21 +0800`
- 范围：插件框架最小可用（发现/健康/能力声明）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_PLUGIN_FRAMEWORK_MIN_20260129.md`
- 报告：`docs/VERIFICATION_PLUGIN_FRAMEWORK_20260129_2121.md`

## Run DOCDOKU-ALIGNMENT-20260129-2344

- 时间：`2026-01-29 23:44 +0800`
- 范围：DocDoku 对标（连接器列表 + 预览/元数据/属性接口）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md`
- 报告：`docs/VERIFICATION_DOCDOKU_ALIGNMENT_20260129_2344.md`

## Run DOCDOKU-ALIGNMENT-20260130-0036

- 时间：`2026-01-30 00:36 +0800`
- 范围：DocDoku 对标（连接器列表 + capabilities + 预览/元数据/属性接口）
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md`
- 报告：`docs/VERIFICATION_DOCDOKU_ALIGNMENT_20260130_0036.md`

## Run CAD-CAPABILITIES-20260130-0048

- 时间：`2026-01-30 00:48 +0800`
- 范围：CAD capabilities 端点验证
- 结果：`ALL CHECKS PASSED`
- 设计：`docs/DESIGN_CAD_CAPABILITIES_ENDPOINT_20260130.md`
- 报告：`docs/VERIFICATION_CAD_CAPABILITIES_20260130_0048.md`

## Run PRIVATE-DELIVERY-POSTGRES-MINIO-20260130-0956

- 时间：`2026-01-30 09:56:18 +0800`
- 基地址：`http://127.0.0.1:7910`
- 运行方式：`scripts/verify_run_h.sh`（Postgres + MinIO）
- 结果：`ALL CHECKS PASSED`
- 说明：验证 Postgres + MinIO 私有化环境；identity DB 迁移已单独跑通（yuantus_identity）

执行命令：

```bash
# 主库迁移
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
  yuantus db upgrade

# identity 分库迁移
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity \
  yuantus db upgrade --identity

# Run H (Postgres + MinIO)
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
  scripts/verify_run_h.sh
```

关键结果（Run H）：

| 验证项 | 结果 | 关键 ID |
| --- | --- | --- |
| Health | ✅ | ok=true |
| AML add/get | ✅ | Part: `d7d058cc-0a17-477b-b4db-e496997a4ee2` |
| Search | ✅ | total>=1 |
| RPC Item.create | ✅ | Part: `6f6869cd-7a59-4a77-91fe-3d6f72837aef` |
| File upload/download | ✅ | file_id: `da080c9d-158f-4ad9-84e9-5498beda9c8a` |
| BOM effective | ✅ | children=[] |
| Plugins | ✅ | yuantus-demo: active |
| ECO 全流程 | ✅ | ECO: `e58dfd47-a9b4-4fb3-85cc-b3f041e34db4` |
| Versions history/tree | ✅ | version_id: `34a3d2bd-d63e-4f4a-b2d1-5cd58d733170` |
| Integrations | ✅ | ok=false（外部服务未启动，预期） |

## Run PRIVATE-DELIVERY-IDENTITY-ENABLED-20260130-1030

- 时间：`2026-01-30 10:30:58 +0800`
- 基地址：`http://127.0.0.1:7910`
- 运行方式：`scripts/verify_run_h.sh`（Postgres + MinIO + identity 分库）
- 结果：`ALL CHECKS PASSED`
- 说明：启用 `YUANTUS_IDENTITY_DATABASE_URL` + `TENANCY_MODE=db-per-tenant-org`，并确保 tenant/org 数据库已迁移到最新版本。

执行命令：

```bash
# identity 分库存在但无 alembic_version 时，先打标
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  yuantus db stamp --identity

# tenant/org 数据库迁移到 head
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 \
  yuantus db upgrade

# Run H (db-per-tenant-org + identity DB)
TENANCY_MODE=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  scripts/verify_run_h.sh
```

关键结果（Run H）：

| 验证项 | 结果 | 关键 ID |
| --- | --- | --- |
| Health | ✅ | ok=true |
| AML add/get | ✅ | Part: `2d2bbafd-40c8-49a6-b732-01b08ed1a29d` |
| Search | ✅ | total>=1 |
| RPC Item.create | ✅ | Part: `8461f8ac-bf1d-450d-a9b3-eba54a01175f` |
| File upload/download | ✅ | file_id: `c39cfdd1-dff4-468b-9901-cd911a015a2f` |
| BOM effective | ✅ | children=[] |
| Plugins | ✅ | yuantus-demo: active |
| ECO 全流程 | ✅ | ECO: `b3a8bfcc-cf3c-46af-bda2-5396f82cfc03` |
| Versions history/tree | ✅ | version_id: `bf3248a2-46c3-4638-915c-e8e0f8899b1c` |
| Integrations | ✅ | ok=false（外部服务未启动，预期） |

## Run CAD-PIPELINE-S3-20260130-1219

- 时间：`2026-01-30 12:19:37 +0800`
- 基地址：`http://127.0.0.1:7910`
- 运行方式：`scripts/verify_cad_pipeline_s3.sh`（Postgres + MinIO + identity 分库）
- 结果：`ALL CHECKS PASSED`
- 备注：控制台提示 `cadquery not installed`（不影响 STL 预览/几何产出）；发现 1 条历史遗留 job 报 “Source file missing” 警告，本次新增的 preview/geometry job 均 completed。

执行命令：

```bash
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  scripts/verify_cad_pipeline_s3.sh
```

关键结果：

| 验证项 | 结果 | 关键 ID |
| --- | --- | --- |
| CAD import | ✅ | file_id: `abcecd7a-676c-4b92-a4a6-338965425ebd` |
| Preview job | ✅ | job_id: `46069eff-cd85-4fb4-98e4-23ed4a7fa1de` |
| Geometry job | ✅ | job_id: `a2d542e3-4cce-4bef-82b3-39cfdb140a72` |
| Preview endpoint | ✅ | HTTP 302（presigned URL） |
| Geometry endpoint | ✅ | HTTP 302（presigned URL） |

## Run CAD-JOB-DIAGNOSTICS-FAILURE-20260130-2141

- 时间：`2026-01-30 21:41:05 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（失败场景诊断可见）
- 说明：模拟“源文件缺失”导致 cad_extract 失败，验证 job 诊断、cad_change_logs 与 conversion_error 落库。

关键验证：

- 失败 job：`a545c9db-3c73-4a52-9503-766a457d72e6`（task=cad_extract）
- file_id：`abcecd7a-676c-4b92-a4a6-338965425ebd`
- /api/v1/jobs/{id} diagnostics：包含 `resolved_source_path`、`cad_format`、`preview_path` 等
- payload.error.code：`source_missing`
- cad_change_logs：记录 `job_failed` + error_code
- meta_files.conversion_error：已写入错误信息

检查命令：

```bash
# 1) API diagnostics
curl -s http://127.0.0.1:7910/api/v1/jobs/a545c9db-3c73-4a52-9503-766a457d72e6 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 2) cad_change_logs（Postgres）
psql postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 \
  -c "SELECT action, payload FROM cad_change_logs WHERE file_id='abcecd7a-676c-4b92-a4a6-338965425ebd' ORDER BY created_at DESC LIMIT 1;"

# 3) conversion_error（Postgres）
psql postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 \
  -c "SELECT conversion_status, conversion_error FROM meta_files WHERE id='abcecd7a-676c-4b92-a4a6-338965425ebd';"
```

## Run CAD-DEDUP-VISION-20260130-2231

- 时间：`2026-01-30 22:31:55 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS（外部 dedup 服务不可达时返回可解释失败，cad_dedup 为空，接口 404）`
- 说明：验证 `cad_dedup_vision` 结果持久化与 `/api/v1/file/{id}/cad_dedup` 读取路径；由于 dedup 服务当前不可达，任务返回 ok=false（不触发重试风暴），`cad_dedup_path` 未写入。

### 1) 迁移（db-per-tenant-org）

```bash
.venv/bin/yuantus db upgrade --db-url postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1
```

```text
Running: /Users/huazhou/Downloads/Github/Yuantus/.venv/bin/python -m alembic -c /Users/huazhou/Downloads/Github/Yuantus/alembic.ini upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade p1b2c3d4e6a4 -> q1b2c3d4e6a5, add cad_dedup_path to meta_files
```

### 2) 登录获取 Token

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}'
```

### 3) 导入 2D 图纸（仅创建 dedup job）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@docs/samples/cadgf_preview_square.dxf" \
  -F 'create_preview_job=false' \
  -F 'create_geometry_job=false' \
  -F 'create_extract_job=false' \
  -F 'create_bom_job=false' \
  -F 'create_dedup_job=true' \
  -F 'create_ml_job=false'
```

```json
{
  "file_id": "655e481c-ae40-4dec-897c-3d37e97dd64f",
  "filename": "cadgf_preview_square.dxf",
  "checksum": "09ae8b2b87412b8dfa6518c40bcd8fedd32432953bde222203ae6eafb3477174",
  "is_duplicate": true,
  "jobs": [
    {
      "id": "99d08ef5-c8e8-4839-8d90-1871cee85d0a",
      "task_type": "cad_dedup_vision",
      "status": "pending"
    }
  ],
  "cad_dedup_url": null
}
```

### 4) 查询 job 结果（dedup 服务不可达）

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/99d08ef5-c8e8-4839-8d90-1871cee85d0a \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "99d08ef5-c8e8-4839-8d90-1871cee85d0a",
  "task_type": "cad_dedup_vision",
  "status": "completed",
  "payload": {
    "file_id": "655e481c-ae40-4dec-897c-3d37e97dd64f",
    "result": {
      "ok": false,
      "error": "[Errno 101] Network is unreachable",
      "file_id": "655e481c-ae40-4dec-897c-3d37e97dd64f"
    }
  }
}
```

### 5) 读取 dedup 结果（未生成）

```bash
curl -s http://127.0.0.1:7910/api/v1/file/655e481c-ae40-4dec-897c-3d37e97dd64f/cad_dedup \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{"detail":"CAD dedup not available"}
```

## Run CAD-DEDUP-VISION-SUCCESS-20260130-2244

- 时间：`2026-01-30 22:44:06 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（dedup job 成功，cad_dedup_path 持久化，/cad_dedup 302 到 presigned URL）
- 说明：启动本机 DedupCAD Vision（S3/事件总线关闭），使用 PNG 样例避免 DXF 解析错误。

### 1) 启动 DedupCAD Vision（本机 8100）

```bash
cd /Users/huazhou/Downloads/Github/dedupcad-vision
S3_ENABLED=false EVENT_BUS_ENABLED=false python3 start_server.py --port 8100
```

```text
GET http://localhost:8100/health -> 200
```

### 2) 导入 PNG（仅创建 dedup job）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@data/storage/2d/50/_front/front_preview.png" \
  -F 'create_preview_job=false' \
  -F 'create_geometry_job=false' \
  -F 'create_extract_job=false' \
  -F 'create_bom_job=false' \
  -F 'create_dedup_job=true' \
  -F 'create_ml_job=false'
```

```json
{
  "file_id": "2e71482a-b5eb-4a2c-8a25-14dae1895ea6",
  "filename": "front_preview.png",
  "checksum": "bfb43ebb24c0fed87d61ced24b6a921bbe80561332428553322728ba32dd2f38",
  "is_duplicate": false,
  "jobs": [
    {
      "id": "b416c417-278f-440d-94c5-d94f43697045",
      "task_type": "cad_dedup_vision",
      "status": "pending"
    }
  ],
  "cad_dedup_url": null
}
```

### 3) 查询 job 结果（ok=true + cad_dedup_path）

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/b416c417-278f-440d-94c5-d94f43697045 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "b416c417-278f-440d-94c5-d94f43697045",
  "task_type": "cad_dedup_vision",
  "status": "completed",
  "payload": {
    "file_id": "2e71482a-b5eb-4a2c-8a25-14dae1895ea6",
    "result": {
      "ok": true,
      "cad_dedup_path": "cad_dedup/2e/2e71482a-b5eb-4a2c-8a25-14dae1895ea6.json",
      "cad_dedup_url": "/api/v1/file/2e71482a-b5eb-4a2c-8a25-14dae1895ea6/cad_dedup"
    }
  }
}
```

### 4) 读取 dedup 结果

```bash
curl -s -D - -o /dev/null http://127.0.0.1:7910/api/v1/file/2e71482a-b5eb-4a2c-8a25-14dae1895ea6/cad_dedup \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
HTTP/1.1 302 Found
Location: http://localhost:59000/yuantus/cad_dedup/2e/2e71482a-b5eb-4a2c-8a25-14dae1895ea6.json?...(presigned)
```

```json
{"kind":"cad_dedup","file_id":"2e71482a-b5eb-4a2c-8a25-14dae1895ea6","mode":"balanced","search":{"success":true,...}}
```

## Run CAD-DEDUP-VISION-DXF-20260130-2257

- 时间：`2026-01-30 22:57:20 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（DXF dedup job 成功，cad_dedup_path 持久化，/cad_dedup 返回 presigned JSON）
- 说明：使用可解析 DXF 样例 `data/storage/2d/c4/c43ea256-c3a5-4d0f-b809-049f7ef033a8.dxf`；DedupCAD Vision 本机 8100。

### 1) 启动 DedupCAD Vision（本机 8100）

```bash
cd /Users/huazhou/Downloads/Github/dedupcad-vision
S3_ENABLED=false EVENT_BUS_ENABLED=false python3 start_server.py --port 8100
```

```text
GET http://localhost:8100/health -> 200
```

### 2) 导入 DXF（仅创建 dedup job）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@data/storage/2d/c4/c43ea256-c3a5-4d0f-b809-049f7ef033a8.dxf" \
  -F 'create_preview_job=false' \
  -F 'create_geometry_job=false' \
  -F 'create_extract_job=false' \
  -F 'create_bom_job=false' \
  -F 'create_dedup_job=true' \
  -F 'create_ml_job=false'
```

```json
{
  "file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
  "filename": "c43ea256-c3a5-4d0f-b809-049f7ef033a8.dxf",
  "checksum": "6a32e37c894133da2bf2e06896fcc166253bb97a4552476b27b4ae8ad527e36c",
  "is_duplicate": false,
  "jobs": [
    {
      "id": "76ab3fca-58ba-4f52-9d62-0bf24a04c542",
      "task_type": "cad_dedup_vision",
      "status": "pending"
    }
  ],
  "cad_dedup_url": null
}
```

### 3) 查询 job 结果（ok=true + cad_dedup_path）

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/76ab3fca-58ba-4f52-9d62-0bf24a04c542 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "76ab3fca-58ba-4f52-9d62-0bf24a04c542",
  "task_type": "cad_dedup_vision",
  "status": "completed",
  "payload": {
    "file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
    "result": {
      "ok": true,
      "cad_dedup_path": "cad_dedup/31/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e.json",
      "cad_dedup_url": "/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup"
    }
  }
}
```

### 4) 读取 dedup 结果

```bash
curl -s -D - -o /dev/null http://127.0.0.1:7910/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
HTTP/1.1 302 Found
Location: http://localhost:59000/yuantus/cad_dedup/31/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e.json?...(presigned)
```

## Run CAD-DEDUP-BATCH-20260131-1204

- 时间：`2026-01-31 12:04:49 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（批量 dedup job 创建/刷新成功，batch 统计可更新）
- 说明：scope 使用 `file_list`，refresh 汇总 job_status。

### 1) 创建 dedup 规则（batch 使用）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'Content-Type: application/json' \
  -d '{"name":"dedup-batch-rule","document_type":"2d","phash_threshold":10,"feature_threshold":0.85,"combined_threshold":0.8,"detection_mode":"balanced","priority":20,"is_active":true}'
```

```json
{
  "id": "5716115d-91ac-40f2-bb42-1f96ed312508",
  "name": "dedup-batch-rule",
  "document_type": "2d",
  "phash_threshold": 10,
  "feature_threshold": 0.85,
  "combined_threshold": 0.8,
  "detection_mode": "balanced",
  "priority": 20,
  "is_active": true
}
```

### 2) 创建批次（file_list scope）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/batches \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'Content-Type: application/json' \
  -d '{"name":"dedup-batch-1","scope_type":"file_list","scope_config":{"file_ids":["3134c931-dbf6-4e6e-8a8b-e6ec28281e2e"]},"rule_id":"5716115d-91ac-40f2-bb42-1f96ed312508"}'
```

```json
{
  "id": "5ee3cfb4-f7e8-4753-8eca-279133433503",
  "status": "queued",
  "total_files": 0,
  "processed_files": 0,
  "found_similarities": 0
}
```

### 3) 运行批次（创建 jobs）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/batches/5ee3cfb4-f7e8-4753-8eca-279133433503/run \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'Content-Type: application/json' \
  -d '{"mode":"balanced","dedupe":true,"priority":30}'
```

```json
{
  "batch": {
    "id": "5ee3cfb4-f7e8-4753-8eca-279133433503",
    "status": "running",
    "total_files": 1,
    "processed_files": 1,
    "summary": {
      "jobs_created": 1,
      "mode": "balanced",
      "rule_id": "5716115d-91ac-40f2-bb42-1f96ed312508"
    }
  },
  "jobs_created": 1
}
```

### 4) 刷新批次状态

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/batches/5ee3cfb4-f7e8-4753-8eca-279133433503/refresh \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "5ee3cfb4-f7e8-4753-8eca-279133433503",
  "status": "completed",
  "total_files": 1,
  "processed_files": 1,
  "found_similarities": 0,
  "summary": {
    "job_status": {
      "pending": 0,
      "processing": 0,
      "completed": 1,
      "failed": 0,
      "cancelled": 0
    }
  }
}
```

## Run CAD-DEDUP-REVIEW-20260131-1213

- 时间：`2026-01-31 12:13:23 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（review 更新状态与审计字段；尝试创建关系时因文件未绑定 Part 而跳过）
- 说明：通过手动插入 similarity 记录模拟审核流程。

### 1) 插入一条待审核记录（psql）

```bash
docker exec -i yuantus-postgres-1 psql -U yuantus -d yuantus_mt_pg__tenant-1__org-1 -c \
"insert into meta_similarity_records (id, source_file_id, target_file_id, similarity_score, similarity_type, detection_method, detection_params, status, created_at) values ('82dfafe7-dcd9-4993-8e03-78db9fd1e4a8','3134c931-dbf6-4e6e-8a8b-e6ec28281e2e','2e71482a-b5eb-4a2c-8a25-14dae1895ea6',0.92,'visual','manual','{}','pending', now());"
```

### 2) 列出相似记录

```bash
curl -s "http://127.0.0.1:7910/api/v1/dedup/records?limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "total": 1,
  "items": [
    {
      "id": "82dfafe7-dcd9-4993-8e03-78db9fd1e4a8",
      "status": "pending"
    }
  ]
}
```

### 3) 审核记录（confirmed + create_relationship）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/records/82dfafe7-dcd9-4993-8e03-78db9fd1e4a8/review \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'Content-Type: application/json' \
  -d '{"status":"confirmed","comment":"manual confirm","create_relationship":true}'
```

```json
{
  "id": "82dfafe7-dcd9-4993-8e03-78db9fd1e4a8",
  "status": "confirmed",
  "reviewed_by_id": 1,
  "review_comment": "manual confirm",
  "relationship_item_id": null
}
```

```json
{"kind":"cad_dedup","file_id":"3134c931-dbf6-4e6e-8a8b-e6ec28281e2e","mode":"balanced","search":{"success":true,...}}
```

## Run PYTEST-NON-DB-20260201-1858

- 时间：`2026-02-01 18:58:44 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）
- 说明：启用 pytest guardrails（testpaths + norecursedirs + conftest skip DB tests）。

## Run PYTEST-DB-20260201-1846

- 时间：`2026-02-01 18:46:15 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`（配合 `.env`）
- 结果：`PASS`（84 passed）

## Run CAD-DEDUP-RULES-RECORDS-20260131-1147

- 时间：`2026-01-31 11:47:53 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（去重规则可持久化，dedup job 正常执行并写入 cad_dedup_path；本次 DedupCAD Vision 无匹配结果，records 为空）
- 说明：DB tenancy 为 `db-per-tenant-org`，需要对租户库执行迁移；DedupCAD Vision 通过 compose 启动。

### 1) 迁移 tenant DB

```bash
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 .venv/bin/yuantus db upgrade
```

### 2) 启动 DedupCAD Vision（compose）

```bash
docker compose up -d dedup-vision
```

### 3) 登录获取 Token

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}'
```

### 4) 创建 dedup 规则（tenant/org）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'Content-Type: application/json' \
  -d '{"name":"dedup-2d-tenant","document_type":"2d","phash_threshold":10,"feature_threshold":0.85,"combined_threshold":0.8,"detection_mode":"balanced","priority":10,"is_active":true}'
```

```json
{
  "id": "e61b9edc-29d6-4eaf-a646-457f0c6c4377",
  "name": "dedup-2d-tenant",
  "document_type": "2d",
  "phash_threshold": 10,
  "feature_threshold": 0.85,
  "combined_threshold": 0.8,
  "detection_mode": "balanced",
  "priority": 10,
  "is_active": true
}
```

### 5) 列出规则

```bash
curl -s http://127.0.0.1:7910/api/v1/dedup/rules \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
[
  {
    "id": "e61b9edc-29d6-4eaf-a646-457f0c6c4377",
    "name": "dedup-2d-tenant",
    "document_type": "2d",
    "phash_threshold": 10,
    "feature_threshold": 0.85,
    "combined_threshold": 0.8,
    "detection_mode": "balanced",
    "priority": 10,
    "is_active": true
  }
]
```

### 6) 导入 DXF（仅创建 dedup job）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@data/storage/2d/c4/c43ea256-c3a5-4d0f-b809-049f7ef033a8.dxf" \
  -F 'create_preview_job=false' \
  -F 'create_geometry_job=false' \
  -F 'create_extract_job=false' \
  -F 'create_bom_job=false' \
  -F 'create_dedup_job=true' \
  -F 'create_ml_job=false'
```

```json
{
  "file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
  "jobs": [
    {
      "id": "d4f393ee-64b1-44eb-9197-2a920ed3295b",
      "task_type": "cad_dedup_vision",
      "status": "pending"
    }
  ],
  "cad_dedup_url": "/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup"
}
```

### 7) 查询 job 结果（ok=true）

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/d4f393ee-64b1-44eb-9197-2a920ed3295b \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "d4f393ee-64b1-44eb-9197-2a920ed3295b",
  "task_type": "cad_dedup_vision",
  "status": "completed",
  "payload": {
    "file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
    "result": {
      "ok": true,
      "cad_dedup_path": "cad_dedup/31/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e.json",
      "cad_dedup_url": "/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup"
    }
  }
}
```

### 8) 列出相似记录（本次无匹配）

```bash
curl -s "http://127.0.0.1:7910/api/v1/dedup/records?limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "total": 0,
  "items": []
}
```

### 9) 读取 dedup 结果

```bash
curl -s -D - -o /dev/null http://127.0.0.1:7910/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
HTTP/1.1 302 Found
Location: http://localhost:59000/yuantus/cad_dedup/31/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e.json?...(presigned)
```

## Run CAD-DEDUP-VISION-COMPOSE-20260130-2349

- 时间：`2026-01-30 23:49:17 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（compose 启动 dedup-vision 正常处理，cad_dedup_path 持久化，/cad_dedup 302 到 presigned URL）
- 说明：使用 docker compose 启动 DedupCAD Vision（8100->8000），复用 DXF 样例。

### 1) 启动 DedupCAD Vision（compose）

```bash
docker compose up -d dedup-vision
```

### 2) 导入 DXF（仅创建 dedup job）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@data/storage/2d/c4/c43ea256-c3a5-4d0f-b809-049f7ef033a8.dxf" \
  -F 'create_preview_job=false' \
  -F 'create_geometry_job=false' \
  -F 'create_extract_job=false' \
  -F 'create_bom_job=false' \
  -F 'create_dedup_job=true' \
  -F 'create_ml_job=false'
```

```json
{
  "file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
  "filename": "c43ea256-c3a5-4d0f-b809-049f7ef033a8.dxf",
  "checksum": "6a32e37c894133da2bf2e06896fcc166253bb97a4552476b27b4ae8ad527e36c",
  "is_duplicate": true,
  "jobs": [
    {
      "id": "98f31149-2410-4551-bde6-6e7395e14a6f",
      "task_type": "cad_dedup_vision",
      "status": "pending"
    }
  ],
  "cad_dedup_url": "/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup"
}
```

### 3) 查询 job 结果（ok=true + cad_dedup_path）

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/98f31149-2410-4551-bde6-6e7395e14a6f \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "id": "98f31149-2410-4551-bde6-6e7395e14a6f",
  "task_type": "cad_dedup_vision",
  "status": "completed",
  "payload": {
    "file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
    "result": {
      "ok": true,
      "cad_dedup_path": "cad_dedup/31/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e.json",
      "cad_dedup_url": "/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup"
    }
  }
}
```

### 4) 读取 dedup 结果

```bash
curl -s -D - -o /dev/null http://127.0.0.1:7910/api/v1/file/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e/cad_dedup \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```text
HTTP/1.1 302 Found
Location: http://localhost:59000/yuantus/cad_dedup/31/3134c931-dbf6-4e6e-8a8b-e6ec28281e2e.json?...(presigned)
```

```json
{"kind":"cad_dedup","file_id":"3134c931-dbf6-4e6e-8a8b-e6ec28281e2e","mode":"balanced","search":{"success":true,...}}
```

## Run P2-CONFIG-VARIANT-RULES-20260131-1517

- 时间：`2026-01-31 15:17:07 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（VariantRule 生效，Standard 排除，Premium 保留；配置实例缓存有效 BOM）
- 说明：使用新配置选项集 + 变型规则 + effective-bom 端点验证。

### 1) 创建选项集 + 选项

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/config/option-sets \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"Mode-1769843826","label":"Mode","value_type":"string"}'
```

```json
{"id":"f4285131-c5c8-49a6-b4df-57d2b1a6404b"}
```

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/config/option-sets/f4285131-c5c8-49a6-b4df-57d2b1a6404b/options \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"key":"Standard","value":"Standard"}'

curl -s -X POST http://127.0.0.1:7910/api/v1/config/option-sets/f4285131-c5c8-49a6-b4df-57d2b1a6404b/options \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"key":"Premium","value":"Premium"}'
```

### 2) 创建父子 Part + BOM 关系

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"CFG-P2-1769843826","name":"Config P2 Parent"}}'
```

```json
{"id":"a204beac-25c7-4f77-b55b-a01aca09f8d5"}
```

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"CFG-P2-C-1769843826","name":"Config P2 Child"}}'
```

```json
{"id":"45ca9d4f-d0a1-484e-8c76-6e3e6ead2264"}
```

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/bom/a204beac-25c7-4f77-b55b-a01aca09f8d5/children \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"child_id":"45ca9d4f-d0a1-484e-8c76-6e3e6ead2264","quantity":1,"uom":"EA"}'
```

### 3) 创建变型规则（Standard 排除子件）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/config/variant-rules \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"P2 Exclude Standard","parent_item_id":"a204beac-25c7-4f77-b55b-a01aca09f8d5","condition":{"option":"Mode-1769843826","value":"Standard"},"action_type":"exclude","target_item_id":"45ca9d4f-d0a1-484e-8c76-6e3e6ead2264"}'
```

```json
{"id":"9f0e54e1-23fe-41ad-a424-49d73b572511"}
```

### 4) 计算 effective BOM（Standard vs Premium）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/config/effective-bom \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"product_item_id":"a204beac-25c7-4f77-b55b-a01aca09f8d5","selections":{"Mode-1769843826":"Standard"},"levels":2}'
```

```json
{
  "id": "a204beac-25c7-4f77-b55b-a01aca09f8d5",
  "children_count": 0,
  "children": []
}
```

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/config/effective-bom \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"product_item_id":"a204beac-25c7-4f77-b55b-a01aca09f8d5","selections":{"Mode-1769843826":"Premium"},"levels":2}'
```

```json
{
  "id": "a204beac-25c7-4f77-b55b-a01aca09f8d5",
  "children_count": 1
}
```

### 5) 创建产品配置实例（缓存有效 BOM）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/config/configurations \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"product_item_id":"a204beac-25c7-4f77-b55b-a01aca09f8d5","name":"Config Premium","selections":{"Mode-1769843826":"Premium"}}'
```

```json
{
  "id": "f4e30b36-9c70-47fe-9eea-56a500b0bfc9",
  "product_item_id": "a204beac-25c7-4f77-b55b-a01aca09f8d5",
  "selections": {
    "Mode-1769843826": "Premium"
  },
  "children_count": 1
}
```

### 6) 脚本验证

- 脚本：`scripts/verify_config_variant_rules.sh`
- 结果：`PASS`

## Run P1-DEDUP-REVIEW-AUTO-REL-20260131-1224

- 时间：`2026-01-31 12:24:29 +0800`
- 基地址：`http://127.0.0.1:7910`
- 结果：`PASS`（review + create_relationship 自动创建 Part Equivalent 关系，并可双向查询）
- 说明：使用已生成的相似记录（DXF/PNG），为两端文件各自绑定 Part 后执行 review。

### 1) 审核相似记录并创建关系

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/dedup/records/82dfafe7-dcd9-4993-8e03-78db9fd1e4a8/review \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H 'Content-Type: application/json' \
  -d '{"status":"confirmed","comment":"auto link","create_relationship":true}'
```

```json
{
  "id": "82dfafe7-dcd9-4993-8e03-78db9fd1e4a8",
  "source_file_id": "3134c931-dbf6-4e6e-8a8b-e6ec28281e2e",
  "target_file_id": "2e71482a-b5eb-4a2c-8a25-14dae1895ea6",
  "status": "confirmed",
  "reviewed_by_id": 1,
  "review_comment": "auto link",
  "relationship_item_id": "63aa12a8-2428-4dd4-bae1-076630960e17"
}
```

### 2) 校验 Part 等效关系（双向）

```bash
curl -s http://127.0.0.1:7910/api/v1/items/a1c53987-8359-47b7-b87f-49f27d0e86f4/equivalents \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

curl -s http://127.0.0.1:7910/api/v1/items/e8a33067-3b1d-4cb5-9ca3-c7a58b0abb96/equivalents \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

```json
{
  "item_id": "a1c53987-8359-47b7-b87f-49f27d0e86f4",
  "count": 1,
  "equivalents": [
    {
      "id": "63aa12a8-2428-4dd4-bae1-076630960e17",
      "equivalent_item_id": "e8a33067-3b1d-4cb5-9ca3-c7a58b0abb96",
      "relationship": {
        "id": "63aa12a8-2428-4dd4-bae1-076630960e17",
        "item_type_id": "Part Equivalent",
        "similarity_score": 0.92,
        "similarity_record_id": "82dfafe7-dcd9-4993-8e03-78db9fd1e4a8"
      }
    }
  ]
}
```

## Run P3（MBOM + Routing）

- 时间：`2026-01-31 16:05:35 +0800`
- 基地址：`http://127.0.0.1:7910`
- 脚本：`scripts/verify_manufacturing_mbom_routing.sh`
- 说明：覆盖 MBOM 生成、结构读取、Routing + Operations、工时/成本计算。

```bash
bash scripts/verify_manufacturing_mbom_routing.sh http://127.0.0.1:7910 tenant-1 org-1
```

```text
PASS: MBOM + routing + time/cost
```

## Run PYTEST-NON-DB-20260201-2315

- 时间：`2026-02-01 23:15:20 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）

## Run PYTEST-DB-20260201-2316

- 时间：`2026-02-01 23:16:10 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`（配合 `.env`）
- 结果：`PASS`（87 passed）

## Run PLAYWRIGHT-ESIGN-20260201-2344

- 时间：`2026-02-01 23:44:39 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run PLAYWRIGHT-ESIGN-20260201-2359

- 时间：`2026-02-01 23:59:11 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run MIGRATIONS-SQLITE-20260202-0016

- 时间：`2026-02-02 00:16:09 +0800`
- 命令：`rm -f /tmp/yuantus_migrate_verify.db && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini upgrade head`
- 结果：`PASS`
- 说明：SQLite 下 baseline/report 迁移使用 batch_alter_table + 命名外键约束。

## Run MIGRATIONS-SQLITE-DOWNGRADE-20260202-0021

- 时间：`2026-02-02 00:21:39 +0800`
- 命令：`rm -f /tmp/yuantus_migrate_verify.db && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini upgrade head && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini downgrade -1`
- 结果：`PASS`
- 说明：SQLite 下验证新增迁移可回滚（从 v1b2c3d4e7a0 回退到 u1b2c3d4e6a9）。

## Run PLAYWRIGHT-ESIGN-20260202-0021

- 时间：`2026-02-02 00:21:39 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run PLAYWRIGHT-ESIGN-20260202-0813

- 时间：`2026-02-02 08:13:58 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run MIGRATIONS-SQLITE-DOWNGRADE-20260202-0818

- 时间：`2026-02-02 08:18:04 +0800`
- 命令：`rm -f /tmp/yuantus_migrate_verify.db && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini upgrade head && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini downgrade -1`
- 结果：`PASS`
- 说明：SQLite 下验证新增迁移可回滚（从 v1b2c3d4e7a0 回退到 u1b2c3d4e6a9）。

## Run MIGRATIONS-SQLITE-DOWNGRADE-20260202-0830

- 时间：`2026-02-02 08:30:37 +0800`
- 命令：`rm -f /tmp/yuantus_migrate_verify.db && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini upgrade head && YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db python3 -m alembic -c alembic.ini downgrade -1`
- 结果：`PASS`
- 说明：SQLite 下验证新增迁移可回滚（从 v1b2c3d4e7a0 回退到 u1b2c3d4e6a9）。

## Run PLAYWRIGHT-ESIGN-20260202-0830

- 时间：`2026-02-02 08:30:37 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run PLAYWRIGHT-ESIGN-20260202-0922

- 时间：`2026-02-02 09:22:14 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run PYTEST-NON-DB-20260202-0931

- 时间：`2026-02-02 09:31:24 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）

## Run PYTEST-DB-20260202-0931

- 时间：`2026-02-02 09:31:24 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（87 passed, 14 warnings）

## Run PYTEST-NON-DB-20260202-2244

- 时间：`2026-02-02 22:44:13 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）

## Run PYTEST-DB-20260202-2244

- 时间：`2026-02-02 22:44:13 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（91 passed, 14 warnings）

## Run PLAYWRIGHT-ESIGN-20260202-2244

- 时间：`2026-02-02 22:44:13 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run PYTEST-NON-DB-20260202-2323

- 时间：`2026-02-02 23:23:01 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）

## Run PYTEST-DB-20260202-2323

- 时间：`2026-02-02 23:23:01 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（91 passed, 14 warnings）

## Run PLAYWRIGHT-ESIGN-20260202-2323

- 时间：`2026-02-02 23:23:01 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 使用临时 DB `/tmp/yuantus_playwright.db`（TENANCY_MODE=single），自动 seed identity/meta，并覆盖签名原因、清单、签名、验证、撤销流程。

## Run PYTEST-NON-DB-20260203-0855

- 时间：`2026-02-03 08:55:05 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）

## Run PYTEST-DB-20260203-0855

- 时间：`2026-02-03 08:55:05 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（91 passed, 14 warnings）

## Run PLAYWRIGHT-ESIGN-20260203-0855

- 时间：`2026-02-03 08:55:05 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：本次输出包含 cadquery 未安装与 Elasticsearch library 未安装提示，但测试通过。

## Run PYTEST-NON-DB-20260203-0856

- 时间：`2026-02-03 08:56:21 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（11 passed）

## Run PYTEST-DB-20260203-0856

- 时间：`2026-02-03 08:56:21 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（94 passed, 14 warnings）

## Run PLAYWRIGHT-ESIGN-20260203-0856

- 时间：`2026-02-03 08:56:21 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：包含 cadquery/Elasticsearch library 未安装提示，但测试通过。

## Run VERIFY-ALL-20260203-1513

- 时间：`2026-02-03 15:13:44 +0800`
- 命令：`MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_1458.log`
- 结果：`FAIL`（PASS: 28 / FAIL: 7 / SKIP: 18）
- 失败项：
  - `Run H (Core APIs)`：迁移时触发 Alembic `u1b2c3d4e6a9`（Postgres）`add_column()` 参数错误
  - `S4 (ECO Advanced)`：viewer 登录失败（无 access_token）
  - `S5-A (CAD 2D Preview)`：`JobFatalError: File not found`
  - `S5-C (CAD Attribute Sync)`：job 直跑后 `Job not found`
  - `S5-C (CAD OCR Title Block)`：`JobFatalError: File not found`
  - `S7 (Multi-Tenancy)`：多租户登录失败
  - `MBOM Convert`：MBOM root 未落库（DB 校验失败）
- 日志：`/tmp/verify_all_20260203_1458.log`

## Run RUN-H-20260203-1450

- 时间：`2026-02-03 14:50:35 +0800`
- 命令：`MIGRATE_TENANT_DB=1 ./scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`
- 说明：启用自动租户库迁移（`scripts/migrate_tenant_db.sh`），TENANCY_MODE=db-per-tenant-org，SQLite 派生库。

## Run VERIFY-ALL-20260203-1545

- 时间：`2026-02-03 15:29:40 +0800`
- 命令：`MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_1545.log`
- 结果：`PASS`（PASS: 35 / FAIL: 0 / SKIP: 18）
- 日志：`/tmp/verify_all_20260203_1545.log`

## Run VERIFY-ALL-20260203-154533

- 时间：`2026-02-03 15:46:52 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_154533.log`
- 结果：`PASS`（PASS: 41 / FAIL: 0 / SKIP: 12）
- 说明：启用 UI 聚合校验；Ops S8 因 audit 未启用而跳过。
- 日志：`/tmp/verify_all_20260203_154533.log`

## Run VERIFY-ALL-20260203-155031

- 时间：`2026-02-03 15:51:30 +0800`
- 命令：`RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_155031.log`
- 结果：`PASS`（PASS: 37 / FAIL: 0 / SKIP: 16）
- 说明：启用审计（`YUANTUS_AUDIT_ENABLED=true`），S8 Ops Monitoring 通过。
- 日志：`/tmp/verify_all_20260203_155031.log`

## Run PLAYWRIGHT-ESIGN-20260203-1552

- 时间：`2026-02-03 15:52:14 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（1 passed）
- 说明：Playwright CLI 启动临时单租户服务并执行 e-sign 端到端流程。

## Run VERIFY-ALL-20260203-155637

- 时间：`2026-02-03 15:57:46 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_155637.log`
- 结果：`PASS`（PASS: 43 / FAIL: 0 / SKIP: 10）
- 说明：启用审计（`YUANTUS_AUDIT_ENABLED=true`），UI 聚合与 Ops S8 全量通过。
- 日志：`/tmp/verify_all_20260203_155637.log`（归档：`docs/verification-logs/20260203/verify_all_20260203_155637.log`）

## Run FULL-REGRESSION-20260203-155800

- 时间：`2026-02-03 15:59:38 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 scripts/run_full_regression.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_20260203_155800.log`
- 结果：`PASS`（PASS: 51 / FAIL: 0 / SKIP: 2）
- 说明：包含真实 2D 连接器、覆盖率、Auto Part、Extractor（external/service）、Real Samples 与 Tenant Provisioning。
- 日志：`/tmp/verify_all_full_20260203_155800.log`（归档：`docs/verification-logs/20260203/verify_all_full_20260203_155800.log`）

## Run PYTEST-BASELINE-FILTERS-20260203-2321

- 时间：`2026-02-03 23:21:40 +0800`
- 命令：`./.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_baseline_enhanced.py`
- 结果：`PASS`（5 passed, 2 warnings）

## Run BASELINE-FILTERS-SCRIPT-20260203-2352

- 时间：`2026-02-03 23:52:01 +0800`
- 命令：`./scripts/verify_baseline_filters.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`
- 说明：基线列表过滤（类型/范围/状态/生效日期）脚本验证。

## Run FULL-REGRESSION-20260204-0813

- 时间：`2026-02-04 08:15:22 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 scripts/run_full_regression.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_20260204_0813.log`
- 结果：`PASS`（PASS: 50 / FAIL: 0 / SKIP: 4）
- 说明：跳过 Config Variants（`RUN_CONFIG_VARIANTS=0`），Audit Logs / Ops Monitoring 因 `audit_enabled=false` 跳过。
- 日志：`/tmp/verify_all_full_20260204_0813.log`（归档：`docs/verification-logs/20260204/verify_all_full_20260204_0813.log`）

## Run PYTEST-EFFECTIVITY-20260204-1554

- 时间：`2026-02-04 15:54:11 +0800`
- 命令：`./.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_effectivity.py`
- 结果：`PASS`（5 passed）

## Run EFFECTIVITY-EXTENDED-20260204-1554

- 时间：`2026-02-04 15:54:11 +0800`
- 命令：`bash scripts/verify_effectivity_extended.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`

## Run LIFECYCLE-SUSPENDED-20260204-1554

- 时间：`2026-02-04 15:54:11 +0800`
- 命令：`bash scripts/verify_lifecycle_suspended.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`

## Run BOM-OBSOLETE-20260204-1712

- 时间：`2026-02-04 17:12:01 +0800`
- 命令：`bash scripts/verify_bom_obsolete.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`

## Run BOM-WEIGHT-ROLLUP-20260204-1712

- 时间：`2026-02-04 17:12:03 +0800`
- 命令：`bash scripts/verify_bom_weight_rollup.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`

## Run PLAYWRIGHT-BOM-OBSOLETE-WEIGHT-20260204-1713

- 时间：`2026-02-04 17:13:58 +0800`
- 命令：`npx playwright test playwright/tests/bom_obsolete_weight.spec.js`
- 结果：`PASS`（2 passed）
- 说明：Playwright CLI 启动临时单租户服务并执行 BOM Obsolete + Weight Rollup API 流程。

## Run VERIFY-ALL-20260204-1716

- 时间：`2026-02-04 17:20:19 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260204_1716.log`
- 结果：`PASS`（PASS: 45 / FAIL: 0 / SKIP: 13）
- 说明：`RUN_CONFIG_VARIANTS=0`，`audit_enabled=false`；`tenancy_mode=single`，`RUN_TENANT_PROVISIONING=0`；CAD Extractor/Real Samples/Connector Coverage 未启用。
- 日志：`/tmp/verify_all_20260204_1716.log`（归档：`docs/verification-logs/20260204/verify_all_20260204_1716.log`）

## Run VERIFY-ALL-20260204-1727

- 时间：`2026-02-04 17:28:39 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 RUN_CONFIG_VARIANTS=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260204_1727.log`
- 结果：`PASS`（PASS: 48 / FAIL: 0 / SKIP: 10）
- 说明：`RUN_CONFIG_VARIANTS=1`，`audit_enabled=true`；`tenancy_mode=single`，`RUN_TENANT_PROVISIONING=0`；CAD Extractor/Real Samples/Connector Coverage 未启用。
- 日志：`/tmp/verify_all_20260204_1727.log`（归档：`docs/verification-logs/20260204/verify_all_20260204_1727.log`）

## Run PYTEST-BOM-OBSOLETE-WEIGHT-20260204-1738

- 时间：`2026-02-04 17:38:33 +0800`
- 命令：`./.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_bom_obsolete_service.py src/yuantus/meta_engine/tests/test_bom_rollup_service.py src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router.py`
- 结果：`PASS`（8 passed, 18 warnings）

## Run PRODUCT-DETAIL-EXT-20260204-1940

- 时间：`2026-02-04 19:40:14 +0800`
- 命令：`bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`
- 说明：新增 BOM obsolete + weight rollup summaries 校验。

## Run PRODUCT-UI-EXT-20260204-2008

- 时间：`2026-02-04 20:08:17 +0800`
- 命令：`bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`
- 说明：产品 UI 聚合包含 BOM obsolete + weight rollup summaries 校验。

## Run PLAYWRIGHT-PRODUCT-UI-SUMMARIES-20260204-2008

- 时间：`2026-02-04 20:08:17 +0800`
- 命令：`npx playwright test playwright/tests/product_ui_summaries.spec.js`
- 结果：`PASS`（1 passed）

## Run PLAYWRIGHT-PRODUCT-UI-SUMMARIES-20260204-2021

- 时间：`2026-02-04 20:21:39 +0800`
- 命令：`bash scripts/verify_playwright_product_ui_summaries.sh http://127.0.0.1:7910`
- 结果：`PASS`（1 passed）

## Run PYTEST-PRODUCT-DETAIL-SUMMARIES-20260204-2045

- 时间：`2026-02-04 20:45:50 +0800`
- 命令：`./.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_product_detail_service.py`
- 结果：`PASS`（2 passed）
- 说明：覆盖 `/products/{id}` 的 BOM obsolete + weight rollup summaries 聚合分支与权限拒绝分支。

## Run PRODUCT-DETAIL-EXT-20260204-2215

- 时间：`2026-02-04 22:15:34 +0800`
- 命令：`bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`
- 说明：本地 `yuantus start` 启动服务后完成产品详情（含 BOM obsolete + weight rollup summaries）校验。

## Run VERIFY-ALL-20260204-2220

- 时间：`2026-02-04 22:20:53 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`（PASS: 46 / FAIL: 0 / SKIP: 13）
- 说明：本地 `yuantus start` 启动服务执行回归；`RUN_CONFIG_VARIANTS=0`，`audit_enabled=false`；CAD ML/real connectors 等未开启项按脚本跳过。

## Run VERIFY-ALL-20260204-2306

- 时间：`2026-02-04 23:06:49 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 RUN_CONFIG_VARIANTS=1 CAD_ML_BASE_URL=http://127.0.0.1:8001 bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`（PASS: 49 / FAIL: 0 / SKIP: 10）
- 说明：本地启用 `YUANTUS_AUDIT_ENABLED=true`；配置项 `RUN_CONFIG_VARIANTS=1` 生效；CAD ML 通过本地 `cad-ml` stub（`http://127.0.0.1:8001`）提供 health/vision/render/ocr 接口以完成 2D 预览与 OCR 验证。
- 日志：`/tmp/verify_all_20260204-230504.log`（归档：`docs/verification-logs/20260204/verify_all_20260204_2305.log`）

## Run VERIFY-ALL-20260204-2330

- 时间：`2026-02-04 23:30:53 +0800`
- 命令：`RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 RUN_CONFIG_VARIANTS=1 YUANTUS_AUDIT_ENABLED=true CAD_ML_BASE_URL=http://127.0.0.1:8001 YUANTUS_CAD_ML_BASE_URL=http://127.0.0.1:8001 CAD_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/ACAD-布局空白 DXF-2013.dxf" bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`（PASS: 49 / FAIL: 0 / SKIP: 10）
- 说明：使用本地 `cad-ml-platform`（非 Docker，`VISION_PROVIDER=stub`）完成 CAD 预览与 OCR；`verify_config_variants.sh` 改为时间戳命名的 OptionSet，避免重复运行时的 name 冲突。
- 日志：`/tmp/verify_all_cadml_20260204-232928.log`（归档：`docs/verification-logs/20260204/verify_all_cadml_20260204_2329.log`）

## Run PYTEST-TARGETED-P4P5P6-20260207-0921

- 时间：`2026-02-07 09:21:45 +0800`
- 命令：`.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_baseline_router_permissions.py src/yuantus/meta_engine/tests/test_esign_router_permissions.py src/yuantus/meta_engine/tests/test_esign_key_rotation.py src/yuantus/meta_engine/tests/test_search_service_fallback.py src/yuantus/meta_engine/tests/test_report_router_permissions.py`
- 结果：`PASS`（12 passed）
- 说明：覆盖 baseline 权限收口、e-sign 审计权限与密钥轮换、search db-fallback、report allowed_roles。

## Run PYTEST-NON-DB-20260207-0921

- 时间：`2026-02-07 09:21:45 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（16 passed）

## Run PYTEST-DB-20260207-0921

- 时间：`2026-02-07 09:21:45 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（175 passed, 142 warnings）

## Run PLAYWRIGHT-E2E-20260207-0921

- 时间：`2026-02-07 09:21:45 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（9 passed, 1 skipped）

## Run PYTEST-TARGETED-P4P5P6-20260207-0930

- 时间：`2026-02-07 09:30:21 +0800`
- 命令：`.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_baseline_router_permissions.py src/yuantus/meta_engine/tests/test_baseline_enhanced.py src/yuantus/meta_engine/tests/test_esign_router_permissions.py src/yuantus/meta_engine/tests/test_esign_key_rotation.py src/yuantus/meta_engine/tests/test_esign_audit_logs.py src/yuantus/meta_engine/tests/test_search_service_fallback.py src/yuantus/meta_engine/tests/test_report_router_permissions.py`
- 结果：`PASS`（23 passed）
- 说明：补齐 baseline compare/export 与 e-sign audit summary/export 的单测覆盖。

## Run PYTEST-NON-DB-20260207-0930

- 时间：`2026-02-07 09:30:21 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（16 passed）

## Run PYTEST-DB-20260207-0930

- 时间：`2026-02-07 09:30:21 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（179 passed, 142 warnings）

## Run PLAYWRIGHT-E2E-20260207-0930

- 时间：`2026-02-07 09:30:21 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（9 passed, 1 skipped）

## Run STRICT-GATE-20260207-140604

- 时间：`2026-02-07 14:06:04 +0800`
- 命令：`TARGETED_PYTEST_ARGS=src/yuantus/meta_engine/tests/test_manufacturing_release_diagnostics.py bash scripts/strict_gate_report.sh`
- 结果：`PASS`
- 证据：`docs/DAILY_REPORTS/STRICT_GATE_20260207-140604.md`

## Run STRICT-GATE-20260207-150747

- 时间：`2026-02-07 15:07:48 +0800`
- 命令：`TARGETED_PYTEST_ARGS=src/yuantus/meta_engine/tests/test_baseline_release_diagnostics.py bash scripts/strict_gate_report.sh`
- 结果：`PASS`
- 证据：`docs/DAILY_REPORTS/STRICT_GATE_20260207-150747.md`

## Run STRICT-GATE-20260207-151114

- 时间：`2026-02-07 15:11:14 +0800`
- 命令：`TARGETED_PYTEST_ARGS=src/yuantus/meta_engine/tests/test_baseline_release_diagnostics.py bash scripts/strict_gate_report.sh`
- 结果：`PASS`
- 证据：`docs/DAILY_REPORTS/STRICT_GATE_20260207-151114.md`

## Run STRICT-GATE-20260207-205929

- 时间：`2026-02-07 20:59:29 +0800`
- 命令：`TARGETED_PYTEST_ARGS='src/yuantus/meta_engine/tests/test_impact_export_bundles.py src/yuantus/meta_engine/tests/test_release_readiness_export_bundles.py' bash scripts/strict_gate_report.sh`
- 结果：`PASS`
- 证据：`docs/DAILY_REPORTS/STRICT_GATE_20260207-205929.md`

## Run STRICT-GATE-20260207-230224

- 时间：`2026-02-07 23:02:24 +0800`
- 命令：`TARGETED_PYTEST_ARGS='src/yuantus/meta_engine/tests/test_impact_export_bundles.py src/yuantus/meta_engine/tests/test_release_readiness_export_bundles.py src/yuantus/meta_engine/tests/test_item_cockpit_router.py src/yuantus/meta_engine/tests/test_baseline_release_diagnostics.py' bash scripts/strict_gate_report.sh`
- 结果：`PASS`
- 证据：`docs/DAILY_REPORTS/STRICT_GATE_20260207-230224.md`

## Run RUN-H-PG-MINIO-20260212-1657

- 时间：`2026-02-12 16:57:37 +0800`
- 环境：`docker compose -f docker-compose.yml`（Postgres + MinIO + API + Worker，`STORAGE_TYPE=s3`）
- 命令：`docker compose -f docker-compose.yml up -d`
- 命令：`YUANTUS_SCHEMA_MODE=migrations DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 摘要：
  - S3 download：`302->200`（presigned URL 可用）

```text
==> Seed identity/meta
==> Login
==> Health
Health: OK
==> Meta metadata (Part)
Meta metadata: OK
==> AML add/get
AML add: OK (part_id=ec3ba088-839c-46c9-ab19-8f091fed46e1)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=486c2045-a476-40a4-a5b9-b364d1de37f9)
==> File upload/download
File upload: OK (file_id=0699d1e2-a79b-4589-813e-f4551d78e803)
File metadata: OK
File download: OK (http=302->200)
==> BOM effective
BOM effective: OK
==> Plugins
Plugins list: OK
Plugins ping: OK
==> ECO full flow
ECO stage: OK (stage_id=6c94ea53-8d2e-4c88-b72c-1bad270028f9)
ECO create: OK (eco_id=478a57ba-83eb-4e76-9fa8-be22248876b4)
ECO new-revision: OK (version_id=f4543521-7740-40c3-a175-3d65b9a2d546)
ECO approve: OK
ECO apply: OK
==> Versions history/tree
Versions history: OK
Versions tree: OK
==> Integrations health (should be 200 even if services down)
Integrations health: OK (ok=False)

ALL CHECKS PASSED
```
