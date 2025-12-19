# YuantusPLM 验证结果（实际执行记录）

> 完整复现步骤与更多验证项：见 `docs/VERIFICATION.md`。

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
