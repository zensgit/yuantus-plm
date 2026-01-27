# YuantusPLM 验证结果（开发环境）

本文档记录 `yuantus-plm` 当前阶段（Meta Engine 内核 + 基础 API + 部分扩展路由）的可用性验证结果与复现命令。

## 验证环境

- API 基地址：`http://127.0.0.1:7910`
- 最近一次验证：`2025-12-18 21:48 +0800`
- 必需请求头：
  - `x-tenant-id: tenant-1`
  - `x-org-id: org-1`
- 默认数据库（dev）：`sqlite:///yuantus_dev.db`
- 可选多租户模式（dev 友好）：`YUANTUS_TENANCY_MODE=db-per-tenant`
  - sqlite 下默认派生：`yuantus_dev__{tenant_id}.db`（例如 `yuantus_dev__tenant-1.db`）
- 可选多组织强隔离模式（dev 友好）：`YUANTUS_TENANCY_MODE=db-per-tenant-org`
  - sqlite 下默认派生：`yuantus_dev__{tenant_id}__{org_id}.db`（例如 `yuantus_dev__tenant-1__org-1.db`）
- 说明：当 `TENANCY_MODE` 为 `db-per-tenant` / `db-per-tenant-org` 时，所有需要 DB 的接口必须提供 tenant/org 上下文，否则返回 400。
- CLI：
  - 主命令：`yuantus`
  - 兼容别名：`plm`

## 启动步骤

1) 安装依赖并启动服务：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
yuantus start --reload --port 7910
```

（可选）以 db-per-tenant 多租户模式启动：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant
yuantus start --reload --port 7910
```

（可选）以 db-per-tenant-org 多组织强隔离模式启动：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
yuantus start --reload --port 7910
```

2)（可选）初始化内置账号/组织（Auth，dev）：

```bash
yuantus seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin
```

> 默认 `YUANTUS_AUTH_MODE=optional`：不带 Token 也能跑通现有验证；要强制鉴权请设置：
>
> ```bash
> export YUANTUS_AUTH_MODE=required
> ```
>
> 当 `YUANTUS_AUTH_MODE=required` 时：除 `GET /api/v1/health`、`POST /api/v1/auth/login`（以及 `/docs`/`/openapi.json`）外，其它接口都会强制要求 `Authorization: Bearer <token>`。

2) 初始化最小元数据（只需执行一次，或在清库后重跑）：

```bash
yuantus seed-meta
```

（可选）在 db-per-tenant 模式下，为指定租户初始化：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant yuantus seed-meta --tenant tenant-1
YUANTUS_TENANCY_MODE=db-per-tenant yuantus seed-meta --tenant tenant-2
```

（可选）在 db-per-tenant-org 模式下，为指定 tenant+org 初始化：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org yuantus seed-meta --tenant tenant-1 --org org-1
YUANTUS_TENANCY_MODE=db-per-tenant-org yuantus seed-meta --tenant tenant-1 --org org-2
```

> 说明：`seed-meta` 会写入 `ItemType=Part/Part BOM/Document`、基础属性，以及 dev 环境默认权限集（`world` 具备 CRUD）。

---

## 验证项汇总

- ✅ `GET /api/v1/health`：服务存活、租户/组织上下文透传
- ✅ `yuantus seed-meta`：写入最小元模型 + 默认权限
- ✅ `GET /api/v1/aml/metadata/Part`：元数据读取（字段/必填/默认值）
- ✅ `POST /api/v1/aml/apply`：AML add/get（创建与查询 Part）
- ✅ `GET /api/v1/search`：搜索（DB fallback）
- ✅ `POST /api/v1/rpc`：统一 RPC（Item.create）
- ✅ `GET /api/v1/bom/{item_id}/effective`：BOM 结构（无子件时 children 为空）
- ✅ `POST /api/v1/file/upload`：文件上传（支持去重）
- ✅ `GET /api/v1/file/{file_id}`：文件元数据查询
- ✅ `GET /api/v1/file/{file_id}/download`：文件下载
- ✅ `POST /api/v1/file/attach`：附件挂载到 Item
- ✅ `GET /api/v1/file/item/{item_id}`：查询 Item 附件列表
- ✅ `GET /api/v1/products/{item_id}`：产品详情聚合（属性/版本/附件）
- ✅ `GET /api/v1/bom/{item_id}/where-used` + `GET /api/v1/bom/compare` + `POST /api/v1/bom/{bom_line_id}/substitutes`：BOM UI 关键接口
- ✅ `scripts/verify_docs_approval.sh`：文档流程 + ECO 审批基础闭环
- ✅ `scripts/verify_cad_connectors.sh`：GStarCAD/ZWCAD 等 2D 连接器验证
- ✅ `scripts/verify_ops_hardening.sh`：多租户/配额/审计/健康/索引回归
- ✅ 文档生命周期：Draft → Review → Released（Released 状态强制锁定更新与附件）
- ✅ Part 生命周期：Draft → Review → Released（Released 状态锁定 BOM/更新/附件）
- ✅ `POST /api/v1/cad/import` + `cad_preview`：CAD 导入 → 异步预览任务 → `GET /api/v1/file/{file_id}/preview`
- ✅ `POST /api/v1/eco`：创建 ECO（变更单）
- ✅ `POST /api/v1/eco/{eco_id}/new-revision`：为 ECO 创建目标版本（分支）
- ✅ `POST /api/v1/eco/{eco_id}/approve` + `POST /api/v1/eco/{eco_id}/apply`：审批并应用 ECO（最小闭环）
- ✅ `GET /api/v1/eco/kanban`：按 Stage 聚合 ECO（看板）
- ✅ `GET /api/v1/plugins`：插件列表与状态（Plugin Manager）
- ✅ `GET /api/v1/plugins/demo/ping`：示例插件路由
- ✅ `POST /api/v1/versions/items/{item_id}/init`：版本初始化
- ✅ `GET /api/v1/versions/items/{item_id}/history`：版本历史
- ✅ `GET /api/v1/versions/items/{item_id}/tree`：版本树
- ✅ `POST /api/v1/auth/login`：登录并签发 JWT（内置账号）
- ✅ `GET /api/v1/auth/orgs`：列出当前用户可用组织
- ⚠️ `GET /api/v1/integrations/health`：聚合外部服务健康（外部服务未启动/缺少鉴权会显示失败，但接口本身稳定返回）

---

## 1) Health

```bash
curl -s http://127.0.0.1:7910/api/v1/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：`200`，返回 `ok=true` 且回显 `tenant_id/org_id`。

示例输出（实际）：

```json
{"ok":true,"service":"yuantus-plm","version":"0.1.0","tenant_id":"tenant-1","org_id":"org-1","tenancy_mode":"single","schema_mode":"create_all"}
```

## 2) Seed Meta（最小元模型）

```bash
yuantus seed-meta
```

示例输出（实际）：

```text
Seeded meta schema: Part, Part BOM, Document
```

## 3) Meta：读取 Part 字段定义

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/metadata/Part \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：`200`，返回 `Part` 的字段列表（含必填 `item_number`）。

## 4) AML：创建 Part（add）

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-0002","name":"Demo Part 2"}}'
```

期望：`200`，返回 `{"id": "...", "type": "Part", "status": "created"}`。

## 5) AML：查询 Part（get）

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"get","properties":{"item_number":"P-0001"}}'
```

期望：`200`，返回 `count/items` 列表。

## 6) Search：按关键词检索（DB fallback）

```bash
curl -s 'http://127.0.0.1:7910/api/v1/search/?q=P-0001&item_type=Part' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：`200`，返回 `{hits:[...], total:N}`。

## 7) RPC：创建 Part（Item.create）

```bash
curl -s http://127.0.0.1:7910/api/v1/rpc/ \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"model":"Item","method":"create","args":[{"type":"Part","properties":{"item_number":"P-0003","name":"RPC Part"}}],"kwargs":{}}'
```

期望：`200`，返回：

```json
{"result":{"id":"...","type":"Part","status":"created"}}
```

## 8) BOM：查询有效 BOM（无子件时为空）

```bash
curl -s http://127.0.0.1:7910/api/v1/bom/<PART_ID>/effective \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：`200`，返回树结构，且 `children` 为数组。

## 9) Integrations：外部服务聚合健康

```bash
curl -s http://127.0.0.1:7910/api/v1/integrations/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

说明：
- Athena 若启用鉴权，需额外传 `Authorization`，例如：
  ```bash
  -H 'Authorization: Bearer <token>'
  ```
- 推荐使用独立 header 给 Athena（避免 Yuantus JWT 冲突）：
  ```bash
  -H 'X-Athena-Authorization: Bearer <athena_token>'
  ```
- 如需服务级认证，可在环境变量设置：
  `YUANTUS_ATHENA_SERVICE_TOKEN=<token>`（自动补 `Bearer ` 前缀）。
- 如使用 client credentials，可通过文件方式注入：
  `YUANTUS_ATHENA_CLIENT_SECRET_FILE=/run/secrets/athena_client_secret`。
- 部署建议：在可提交的 `docker-compose.yml` 或 `.env` 中设置
  `YUANTUS_ATHENA_BASE_URL=http://host.docker.internal:7700/api/v1`，避免只写在
  `docker-compose.override.yml`（已被 `.gitignore` 忽略）。
- Athena 侧健康检查默认走 `/api/v1/system/status`（兼容旧部署会回退到 `/health`）。
- 当外部服务未启动/无鉴权时，本接口仍返回 `200`，并在各服务节点里显示错误原因（如 `401` 或连接失败）。

联测示例（推荐）：

```bash
# Yuantus token
YUANTUS_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Athena token (Keycloak)
ATHENA_TOKEN=$(curl -s -X POST http://localhost:8180/realms/ecm/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password&client_id=unified-portal&username=admin&password=admin' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s http://127.0.0.1:7910/api/v1/integrations/health \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $YUANTUS_TOKEN" \
  -H "X-Athena-Authorization: Bearer $ATHENA_TOKEN"
```

示例输出（实际，外部服务未启动/未鉴权）：

```json
{"ok":false,"tenant_id":"tenant-1","org_id":"org-1","services":{"athena":{"ok":false,"base_url":"http://localhost:7700/api/v1","status_code":401,"error":""},"cad_ml":{"ok":false,"base_url":"http://localhost:8001","error":"All connection attempts failed"},"dedup_vision":{"ok":false,"base_url":"http://localhost:8100","error":"All connection attempts failed"}}}
```

---

## 已知限制（当前阶段）

- 多租户/多组织默认仍是“请求上下文透传（Header -> ContextVar）”；已提供可选 `db-per-tenant`（按租户独立 DB 文件）模式，但尚未实现 schema-per-tenant / row-level 隔离策略。
- CAD 预览/转换仍依赖外部组件（如 FreeCAD/cadquery），当前已验证 `cad_preview` 任务链路可跑通；未安装 Pillow/FreeCAD 时会生成占位预览图。
- ECO 当前验证的是“最小闭环”（创建→new-revision→审批→apply）；BOM 差异计算目前仅做 level-1 对比，深层 BOM/高级冲突解决仍在迭代中。

---

## 10) File：上传/下载/挂载（基础文件能力）

### 10.1 上传文件

```bash
curl -s 'http://127.0.0.1:7910/api/v1/file/upload?generate_preview=false' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F 'file=@/tmp/yuantus_upload_test.txt;filename=yuantus_upload_test.txt'
```

期望：`200`，返回 `id/url/size`；同内容重复上传会命中去重并返回同一个 `id`。

示例输出（实际）：

```json
{"id":"e210f978-d981-44a2-beba-942a79a3888a","filename":"yuantus_upload_test.txt","url":"/api/v1/file/e210f978-d981-44a2-beba-942a79a3888a/download","size":25,"mime_type":"text/plain","is_cad":false,"preview_url":null}
```

### 10.2 查询元数据

```bash
curl -s http://127.0.0.1:7910/api/v1/file/<FILE_ID> \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

### 10.3 下载文件

```bash
curl -s http://127.0.0.1:7910/api/v1/file/<FILE_ID>/download \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

### 10.4 挂载附件到 Item（如 Part）

```bash
curl -s http://127.0.0.1:7910/api/v1/file/attach \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"item_id":"<PART_ID>","file_id":"<FILE_ID>","file_role":"attachment","description":"test attach"}'
```

### 10.5 查询 Item 的附件列表

```bash
curl -s http://127.0.0.1:7910/api/v1/file/item/<PART_ID> \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 11) 多租户隔离（db-per-tenant）

前提：

- 以 `YUANTUS_TENANCY_MODE=db-per-tenant` 启动服务
- 分别对租户执行 `seed-meta`

### 11.1 tenant-1 创建数据

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"T1-001","name":"Tenant1 Part"}}'
```

### 11.2 tenant-1 可查到，tenant-2 查不到

```bash
# tenant-1
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"get"}'

# tenant-2
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-2' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"get"}'
```

---

## 12) 多组织隔离（db-per-tenant-org）

前提：

- 以 `YUANTUS_TENANCY_MODE=db-per-tenant-org` 启动服务
- 对同一 tenant 下的不同 org 分别执行 `seed-meta`

### 12.1 tenant-1 / org-1 创建数据

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"O1-001","name":"Org1 Part"}}'
```

### 12.2 org-1 可查到，org-2 查不到

```bash
# org-1
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"get"}'

# org-2
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-2' \
  -d '{"type":"Part","action":"get"}'
```

---

## 13) Versions：版本初始化/历史/树（基础版本能力）

### 13.1 初始化版本（init）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/versions/items/<PART_ID>/init \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：`200`，返回 `revision=A`、`version_label=1.A`，并回显 `properties` 快照。

示例输出（实际）：

```json
{"id":"3c7ca75e-35a7-4262-934f-69c51f903618","item_id":"969300ca-35ce-43b1-8a4a-bb28638f640a","generation":1,"revision":"A","version_label":"1.A","state":"Draft","is_current":true,"is_released":false,"properties":{"item_number":"P-VERIFY-0001","name":"Verify Part","state":"New"},"created_by_id":1,"created_at":"2025-12-18T01:11:49.699520","branch_name":"main","file_count":0}
```

### 13.2 查看版本历史（history）

```bash
curl -s http://127.0.0.1:7910/api/v1/versions/items/<PART_ID>/history \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
[{"version_id":"3c7ca75e-35a7-4262-934f-69c51f903618","action":"create","comment":"Initial version created","changes":null,"id":"90460c64-d31e-415e-af2f-552dcb57bcf3","user_id":1,"created_at":"2025-12-18T01:11:49.701196"}]
```

### 13.3 查看版本树（tree）

```bash
curl -s http://127.0.0.1:7910/api/v1/versions/items/<PART_ID>/tree \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
[{"id":"3c7ca75e-35a7-4262-934f-69c51f903618","label":"1.A","predecessor_id":null,"branch":"main","state":"Draft","created_at":"2025-12-18T01:11:49.699520"}]
```

---

## 14) ECO：创建→new-revision→审批→apply（最小闭环）

> 说明：ECO 相关接口统一在 `/api/v1/eco` 下；操作者 `user_id` 由 JWT（`Authorization: Bearer ...`）决定，不再接受 `user_id` query 参数冒充。

### 14.1（可选）创建 Stage

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/eco/stages \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"Review","sequence":10,"approval_type":"mandatory","approval_roles":["admin"],"is_blocking":false,"auto_progress":false,"description":"MVP review stage"}'
```

示例输出（实际）：

```json
{"id":"a705ae1d-5631-47d9-880d-8b5ae5e4dcfd","name":"Review","sequence":10,"approval_type":"mandatory"}
```

### 14.2 创建一个产品（Part）

```bash
curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"ECO-PROD-001","name":"ECO Product"}}'
```

示例输出（实际）：

```json
{"id":"d63e8e94-f69b-4eac-ad99-03eef2096f77","type":"Part","status":"created"}
```

### 14.3 创建 ECO（绑定 product_id）

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"ECO-001","eco_type":"bom","product_id":"<PART_ID>","description":"MVP ECO","priority":"normal"}'
```

示例输出（实际）：

```json
{"id":"f30a3c5f-d75c-4606-9ad2-44a4d2bee9af","name":"ECO-001","eco_type":"bom","product_id":"d63e8e94-f69b-4eac-ad99-03eef2096f77","source_version_id":null,"target_version_id":null,"stage_id":"a705ae1d-5631-47d9-880d-8b5ae5e4dcfd","state":"draft","kanban_state":"normal","priority":"normal","description":"MVP ECO","product_version_before":null,"product_version_after":null,"effectivity_date":null,"created_by_id":1,"created_at":"2025-12-18T01:55:39.948926","updated_at":"2025-12-18T01:55:39.951196"}
```

### 14.4 new-revision：为 ECO 创建目标版本（分支）

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/new-revision' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
{"success":true,"version_id":"36c5088c-a53c-4583-8075-902a383a4fcd","version_label":"1.A-eco-f30a3c5f"}
```

### 14.5 pending + approve：审批 ECO

```bash
curl -s 'http://127.0.0.1:7910/api/v1/eco/approvals/pending' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
[{"eco_id":"f30a3c5f-d75c-4606-9ad2-44a4d2bee9af","eco_name":"ECO-001","eco_state":"progress","stage_id":"a705ae1d-5631-47d9-880d-8b5ae5e4dcfd","stage_name":"Review","approval_type":"mandatory"}]
```

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/approve' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"comment":"approved"}'
```

示例输出（实际）：

```json
{"id":"9f0bfb05-ae67-46a1-afac-2dc6eb0def85","eco_id":"f30a3c5f-d75c-4606-9ad2-44a4d2bee9af","stage_id":"a705ae1d-5631-47d9-880d-8b5ae5e4dcfd","approval_type":"mandatory","required_role":null,"user_id":1,"status":"approved","comment":"approved","approved_at":"2025-12-18T01:56:34.349940","created_at":"2025-12-18T01:56:34.350303"}
```

### 14.6 apply：应用 ECO（将 target_version 设为当前版本，并把 ECO 标记为 done）

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/apply' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
{"success":true,"message":"ECO applied successfully"}
```

### 14.7 验证：产品 current_version_id 已切换到 ECO 的 target_version_id

```bash
curl -s http://127.0.0.1:7910/api/v1/bom/<PART_ID>/effective \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际，节选）：

```json
{"current_version_id":"36c5088c-a53c-4583-8075-902a383a4fcd"}
```

### 14.8 看板视图（按 Stage 聚合 ECO）

```bash
curl -s http://127.0.0.1:7910/api/v1/eco/kanban \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 15) Plugins：插件列表与示例插件路由

> 默认插件目录：`./plugins`（可用 `YUANTUS_PLUGIN_DIRS` 覆盖）。

### 15.1 查看插件列表与状态

```bash
curl -s http://127.0.0.1:7910/api/v1/plugins \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
{"ok":true,"plugins":[{"id":"yuantus-demo","name":"Yuantus Demo Plugin","version":"0.1.0","description":"Demo plugin that adds a simple API route.","author":"YuantusPLM","status":"active","is_active":true,"plugin_type":"extension","category":"demo","tags":["demo","plugin"],"dependencies":[],"loaded_at":"2025-12-18T02:33:05.258388+00:00","activated_at":"2025-12-18T02:33:05.258396+00:00","error_count":0,"last_error":null,"plugin_path":"plugins/yuantus-demo"}],"stats":{"total":1,"by_status":{"active":1},"by_type":{"extension":1},"by_category":{"demo":1},"errors":0}}
```

### 15.2 验证示例插件路由

```bash
curl -s http://127.0.0.1:7910/api/v1/plugins/demo/ping \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

示例输出（实际）：

```json
{"ok":true,"plugin":"yuantus-demo"}
```

---

## 16) Jobs：创建后台任务 + Worker 执行

> 用途：为 CAD 转换/预览/去重索引/报表等“异步任务”提供基础能力（模块化/微服务化的核心支撑）。

### 16.1 创建一个示例 Job（cad_conversion）

```bash
curl -s -X POST 'http://127.0.0.1:7910/api/v1/jobs' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"task_type":"cad_conversion","payload":{"input_file_path":"part_a.dwg","output_format":"gltf"}}'
```

期望：`200`，返回 `id/status=pending|processing`。

### 16.2 启动 Worker（执行一次并退出）

```bash
yuantus worker --worker-id worker-verify --poll-interval 1 --once
```

> 多租户/多组织隔离模式下：Worker 必须与 API 使用同一 `YUANTUS_TENANCY_MODE`，并传入相同 `--tenant/--org` 才能处理对应 DB 的任务。

例如（db-per-tenant-org）：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
yuantus worker --tenant tenant-1 --org org-1 --worker-id worker-verify --poll-interval 1 --once
```

### 16.3 查询 Job 状态

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs/<JOB_ID> \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：在 Worker 执行后，`status` 变为 `completed`（或失败时为 `failed` 且带 `last_error`）。

### 16.4 CAD 导入：创建 `cad_preview` 并由 Worker 生成预览

1) 准备测试文件：

```bash
TEST_FILE=/tmp/yuantus_cad_import_test.dwg
echo "dummy dwg $(date)" > "$TEST_FILE"
```

2)（可选，AUTH_MODE=required 时需要）登录获取 Token：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

3) 调用 CAD 导入接口（只创建预览任务，便于验证）：

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

期望：返回 `file_id`，并包含 `task_type=cad_preview` 的 job（`status=pending`）。

4) 运行一次 Worker 执行任务并退出：

```bash
yuantus worker --worker-id worker-cad --poll-interval 1 --once
```

5) 验证预览可获取：

```bash
curl -s -o /tmp/yuantus_preview_test.png -w '%{http_code}\n' \
  http://127.0.0.1:7910/api/v1/file/<FILE_ID>/preview \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

期望：返回 `200` 且输出为 `image/png`。

---

## 17) Auth：登录并调用受保护接口（可选）

### 17.1 登录获取 Token

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}'
```

期望：`200`，返回 `access_token`。

### 17.2 查询当前用户可用组织

```bash
TOKEN='<access_token>'
curl -s http://127.0.0.1:7910/api/v1/auth/orgs \
  -H "Authorization: Bearer $TOKEN"
```

### 17.3（建议）业务接口同时带 tenant/org + Authorization

```bash
curl -s http://127.0.0.1:7910/api/v1/health \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

### 17.4（多组织）切换 Org 并签发新 Token（推荐）

适用场景：用户属于多个组织，希望“用同一个账号在不同 org 下工作”，并让 Token 自带 `org_id`（这样很多业务接口可以不再依赖 `x-org-id` 头）。

1) 先用 tenant 登录（不带 org_id）拿到 Token：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

2) 列出可用组织：

```bash
curl -s http://127.0.0.1:7910/api/v1/auth/orgs \
  -H "Authorization: Bearer $TOKEN"
```

3) 切换到目标组织（签发包含 org_id 的新 Token）：

```bash
ORG_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/switch-org \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"org_id":"org-1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

4) 使用新 Token 调用业务接口（不传 `x-org-id`，由 Token 的 org_id 决定）：

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H 'x-tenant-id: tenant-1'
```

---

## 18) Admin（Identity）：组织/用户/成员管理（dev）

> 说明：本组接口使用 Identity DB（`auth_*` 表），用于多组织/成员管理。
>
> 当前实现：
> - **Tenant 级**（`/api/v1/admin/tenant`、`/api/v1/admin/orgs`、`/api/v1/admin/users`）仅 **Superuser** 可访问
> - **Org 成员管理**（`/api/v1/admin/orgs/{org_id}/members`）允许 **Superuser 或该 org 的 admin/org_admin** 角色访问

### 18.1 获取 admin token（推荐直接用 org-1 登录）

```bash
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

### 18.2 查看当前 tenant 信息

```bash
curl -s http://127.0.0.1:7910/api/v1/admin/tenant \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 18.3 创建 org-2

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/orgs \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"id":"org-2","name":"Org 2"}'
```

### 18.4 创建用户 bob

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/users \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"bob","password":"bob","email":"bob@example.com","is_superuser":false}'
```

### 18.5 将 bob 加入 org-2 并授予角色 engineer

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/orgs/org-2/members \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"bob","roles":["engineer"],"is_active":true}'
```

### 18.6 bob 走“多组织切换”流程（login → orgs → switch-org）

```bash
BOB_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"bob","password":"bob"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s http://127.0.0.1:7910/api/v1/auth/orgs \
  -H "Authorization: Bearer $BOB_TOKEN"

BOB_ORG_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/switch-org \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"org_id":"org-2"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

调用业务接口（不传 `x-org-id`）：

```bash
curl -s http://127.0.0.1:7910/api/v1/jobs \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $BOB_ORG_TOKEN"
```

---

## 19) Meta Permissions：配置权限集并验证 RBAC 生效（dev）

> 说明：Meta Engine 的 `add/get/update/delete/promote` 已内置权限检查（ACL + Lifecycle State）。
>
> 本节通过 API 创建一个权限集，把 `Part` 的权限从默认 `Default` 切换为“仅 engineer 可创建”，用两个用户验证生效。

### 19.1 获取 admin token（需要 admin/superuser 角色）

```bash
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

### 19.2 创建权限集 `PartEngineerOnly`

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/permissions \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"id":"PartEngineerOnly","name":"Part Engineer Only"}'
```

### 19.3 配置 ACE（engineer 可创建/读取/更新；world 只读）

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/permissions/PartEngineerOnly/accesses \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"identity_id":"engineer","can_create":true,"can_get":true,"can_update":true,"can_delete":false,"can_discover":true}'

curl -s -X POST http://127.0.0.1:7910/api/v1/meta/permissions/PartEngineerOnly/accesses \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"identity_id":"world","can_create":false,"can_get":true,"can_update":false,"can_delete":false,"can_discover":true}'
```

### 19.4 将 ItemType=Part 绑定到该权限集

```bash
curl -s -X PATCH http://127.0.0.1:7910/api/v1/meta/item-types/Part/permission \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"permission_id":"PartEngineerOnly"}'
```

### 19.5 创建用户并验证：bob(engineer) ✅ / alice(viewer) ❌

创建 alice 并加入 org-2（role=viewer）：

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/admin/users \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"alice","password":"alice","email":"alice@example.com","is_superuser":false}'

curl -s -X POST http://127.0.0.1:7910/api/v1/admin/orgs/org-2/members \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"alice","roles":["viewer"],"is_active":true}'
```

bob（engineer, org-2）创建 Part（应 `200`）：

```bash
BOB_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"bob","password":"bob","org_id":"org-2"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-RBAC-001","name":"RBAC Part"}}'
```

alice（viewer, org-2）创建 Part（应 `403`）：

```bash
ALICE_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"alice","password":"alice","org_id":"org-2"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -i http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-RBAC-002","name":"RBAC Part 2"}}'
```

---

## 20) S1 验收脚本：Meta Schema + RBAC

### 20.1 一键验收：`scripts/verify_permissions.sh`

此脚本验证 S1 的完整能力：

1. **Meta Schema 管理**：ItemType/Property 创建/更新 API（admin-only）
2. **权限配置闭环**：PermissionSet 创建、ACE 配置、ItemType 绑定
3. **RBAC 执行**：viewer 角色 403、admin 角色 200

```bash
# 启动服务（AUTH_MODE=required）
YUANTUS_AUTH_MODE=required yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_permissions.sh http://127.0.0.1:7910 tenant-1 org-1
```

期望输出：

```text
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Created PermissionSet: ReadOnly-...
ACE viewer (read-only): OK
ACE admin (full): OK
==> Assign PermissionSet to ItemTypes
Assigned permission to Part: OK
Assigned permission to Part BOM: OK
==> Admin creates Part (should succeed)
Admin AML add Part: OK (part_id=...)
Admin created child Part: OK (child_id=...)
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

### 20.2 Meta Schema API 新增端点

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/meta/item-types` | GET | 列出所有 ItemType | 公开 |
| `/api/v1/meta/item-types/{id}` | GET | 获取 ItemType 详情（含 properties） | 公开 |
| `/api/v1/meta/item-types` | POST | 创建 ItemType | admin |
| `/api/v1/meta/item-types/{id}` | PATCH | 更新 ItemType | admin |
| `/api/v1/meta/item-types/{id}/properties` | POST | 创建 Property | admin |
| `/api/v1/meta/item-types/{id}/properties/{prop_id}` | PATCH | 更新 Property | admin |
| `/api/v1/meta/item-types/{id}/properties/{prop_id}` | DELETE | 删除 Property | admin |
| `/api/v1/meta/item-types/{id}/refresh-schema` | POST | 刷新 properties_schema 缓存 | admin |

### 20.3 手动验证 Meta Schema API

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 列出所有 ItemTypes
curl -s http://127.0.0.1:7910/api/v1/meta/item-types \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 创建新 ItemType（admin only）
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/item-types \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"id":"Assembly","label":"Assembly","is_versionable":true}'

# 为 Assembly 添加 Property
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/item-types/Assembly/properties \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"name":"assembly_number","label":"Assembly Number","data_type":"string","is_required":true}'

# 刷新 properties_schema
curl -s -X POST http://127.0.0.1:7910/api/v1/meta/item-types/Assembly/refresh-schema \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 21) S3.1 验收脚本：多级 BOM + 循环检测

### 21.1 一键验收：`scripts/verify_bom_tree.sh`

此脚本验证 S3.1 的完整能力：

1. **BOM 写入 API**：`POST /api/v1/bom/{parent_id}/children` 添加子件
2. **BOM 删除 API**：`DELETE /api/v1/bom/{parent_id}/children/{child_id}` 移除子件
3. **BOM 树查询**：`GET /api/v1/bom/{parent_id}/tree?depth=...` 支持深度限制
4. **循环检测**：添加会形成环的关系返回 `409` 及循环路径

```bash
# 启动服务
yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
```

期望输出：

```text
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create test parts for BOM tree
Created Part A: ...
Created Part B: ...
Created Part C: ...
Created Part D: ...
==> Build BOM structure: A -> B -> C, B -> D
Adding B as child of A...
A -> B relationship created: ...
Adding C as child of B...
B -> C relationship created: ...
Adding D as child of B...
B -> D relationship created: ...
BOM structure created: OK
==> Test BOM tree query with depth
Full tree (depth=10): Level 1 has 1 child (B): OK
Full tree (depth=10): Level 2 has 2 children (C, D): OK
Limited tree (depth=1): Only shows B with no grandchildren: OK
==> Test cycle detection (C -> A should be 409)
Cycle detection: C -> A returned 409: OK
Cycle error type: CYCLE_DETECTED: OK
Cycle path returned: [...]: OK
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

### 21.2 BOM 写入 API 新增端点

| 端点 | 方法 | 说明 | 响应码 |
|------|------|------|--------|
| `/api/v1/bom/{parent_id}/children` | POST | 添加子件到 BOM | 200: 成功, 400: 重复/参数错误, 409: 循环检测 |
| `/api/v1/bom/{parent_id}/children/{child_id}` | DELETE | 从 BOM 移除子件 | 200: 成功, 404: 不存在 |
| `/api/v1/bom/{parent_id}/tree` | GET | 查询 BOM 树结构（支持 depth 参数） | 200: 成功, 404: 父件不存在 |

### 21.3 循环检测响应格式

当添加 BOM 关系会形成循环时，返回 `409 Conflict`：

```json
{
  "error": "CYCLE_DETECTED",
  "message": "Cycle detected: A -> B -> C -> A",
  "parent_id": "...",
  "child_id": "...",
  "cycle_path": ["A-id", "B-id", "C-id", "A-id"]
}
```

### 21.4 手动验证 BOM 写入 API

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 创建测试零件
PART_A=$(curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-TEST-A","name":"Part A"}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

PART_B=$(curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-TEST-B","name":"Part B"}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 添加 B 作为 A 的子件（qty=2, uom=EA, find_num=10）
curl -s -X POST "http://127.0.0.1:7910/api/v1/bom/$PART_A/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d "{\"child_id\":\"$PART_B\",\"quantity\":2,\"uom\":\"EA\",\"find_num\":\"10\"}"

# 查询 BOM 树（depth=10）
curl -s "http://127.0.0.1:7910/api/v1/bom/$PART_A/tree?depth=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 尝试添加循环（B -> A，应返回 409）
curl -s -i -X POST "http://127.0.0.1:7910/api/v1/bom/$PART_B/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d "{\"child_id\":\"$PART_A\",\"quantity\":1}"

# 移除子件
curl -s -X DELETE "http://127.0.0.1:7910/api/v1/bom/$PART_A/children/$PART_B" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 22) S3.2 验收脚本：BOM Effectivity 生效性

### 22.1 一键验收：`scripts/verify_bom_effectivity.sh`

此脚本验证 S3.2 的完整能力：

1. **BOM 行生效性写入**：`POST /api/v1/bom/{parent_id}/children` 传 `effectivity_from/to` 会创建 `meta_effectivities` 记录
2. **生效性过滤**：`/api/v1/bom/{id}/effective?date=...` 按日期过滤 BOM 行
3. **同一 BOM 不同日期不同结果**：TODAY/NEXT_WEEK/LAST_WEEK 返回不同 children
4. **RBAC**：viewer 不能添加 BOM 子件 (403)，但可以读取 effective BOM (200)
5. **CASCADE 删除**：删除 BOM 行时 Effectivity 记录自动清理

```bash
# 启动服务（AUTH_MODE=required）
YUANTUS_AUTH_MODE=required yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_bom_effectivity.sh http://127.0.0.1:7910 tenant-1 org-1
```

期望输出：

```text
Date context: TODAY=..., NEXT_WEEK=..., LAST_WEEK=...
==> Seed identity (admin + viewer)
Created users: admin (superuser), viewer (no write)
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Configure PermissionSets
Permissions configured: OK
==> Create test parts
Created Part A (parent): ...
Created Part B (future child): ...
Created Part C (current child): ...
Created Part D (expired child): ...
==> Build BOM with effectivity dates
Adding B to A (effective from next week)...
A -> B relationship: ..., effectivity_id: ...
Adding C to A (effective from last week, always visible now)...
A -> C relationship: ...
Adding D to A (expired - ended last week)...
A -> D relationship: ...
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

### 22.2 生效性数据模型

BOM 行的生效性存储在 `meta_effectivities` 表：

| 字段 | 说明 |
|------|------|
| `id` | Effectivity 记录 ID |
| `item_id` | BOM relationship Item ID（FK, CASCADE DELETE） |
| `effectivity_type` | 类型：Date / Lot / Serial / Unit |
| `start_date` | 生效开始日期 |
| `end_date` | 生效结束日期 |

### 22.3 API 参数说明

**POST /api/v1/bom/{parent_id}/children**

新增可选参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `effectivity_from` | datetime | 生效开始日期（ISO 8601 格式） |
| `effectivity_to` | datetime | 生效结束日期（ISO 8601 格式） |

响应新增字段：

| 字段 | 说明 |
|------|------|
| `effectivity_id` | 创建的 Effectivity 记录 ID（若传入日期参数） |

**GET /api/v1/bom/{item_id}/effective**

| 参数 | 类型 | 说明 |
|------|------|------|
| `date` | datetime | 查询日期（默认当前时间） |
| `levels` | int | 展开深度（默认 10） |

### 22.4 手动验证生效性过滤

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 创建父件
PARENT=$(curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-EFF-PARENT","name":"Parent"}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 创建子件
CHILD=$(curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-EFF-CHILD","name":"Child"}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 添加子件（生效日期：下周开始）
NEXT_WEEK=$(date -u -d '+7 days' +%Y-%m-%dT%H:%M:%SZ)
curl -s -X POST "http://127.0.0.1:7910/api/v1/bom/$PARENT/children" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d "{\"child_id\":\"$CHILD\",\"quantity\":1,\"effectivity_from\":\"$NEXT_WEEK\"}"

# 查询当前生效 BOM（应无子件）
curl -s "http://127.0.0.1:7910/api/v1/bom/$PARENT/effective" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 查询下周生效 BOM（应有子件）
curl -s "http://127.0.0.1:7910/api/v1/bom/$PARENT/effective?date=$NEXT_WEEK" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 23) S3.3 验收脚本：版本语义与规则固化

### 23.1 一键验收：`scripts/verify_versions.sh`

此脚本验证 S3.3 的版本系统完整能力：

1. **初始版本**：创建 Item 后 init 得到 1.A（generation=1, revision=A）
2. **修订递增**：revise 操作得到 1.B, 1.C...（同 generation，revision 递增）
3. **版本历史/树**：history 和 tree API 返回完整版本链
4. **迭代支持**：在版本内创建 iteration（如 1.C.1, 1.C.2）
5. **修订方案**：支持 letter/number/hybrid/semantic 等 scheme
6. **Checkout/Checkin**：checkout 锁定版本，checkin 解锁

```bash
# 启动服务
yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_versions.sh http://127.0.0.1:7910 tenant-1 org-1
```

期望输出：

```text
==> Seed identity
Created admin user
==> Seed meta schema
==> Login as admin
Admin login: OK
==> Create test part
Created Part: ...
==> Initialize version (should be 1.A)
Initial version: 1.A: OK
Generation: 1, Revision: A: OK
==> Create revision (should be 1.B)
Revise version...
Revision 1.B: OK
==> Create another revision (should be 1.C)
Revision 1.C: OK
==> Get version history
History contains 3 entries: OK
==> Get version tree
Tree shows: 1.A -> 1.B -> 1.C: OK
==> Create iteration on 1.C (should be 1.C.1)
Iteration 1.C.1: OK
==> Create another iteration (should be 1.C.2)
Iteration 1.C.2: OK
==> Test checkout/checkin
Checkout version...
Checkout: state=CheckedOut: OK
Checkin version...
Checkin: state=Released: OK
==> Test revision scheme calculation
A -> B: OK
Z -> AA: OK
AA -> AB: OK

ALL CHECKS PASSED
```

### 23.2 版本数据模型

| 字段 | 说明 |
|------|------|
| `generation` | 主版本号（1, 2, 3...），new_generation 时递增 |
| `revision` | 修订号（A, B, C...Z, AA, AB...），revise 时递增 |
| `version_label` | 完整标签（如 "1.A", "2.B"） |
| `state` | 状态：Draft / CheckedOut / Released / Obsolete |
| `is_current` | 是否为当前活跃版本 |
| `is_released` | 是否已发布（不可再修改） |
| `branch_name` | 分支名（默认 "main"） |

### 23.3 版本 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/versions/items/{item_id}/init` | POST | 初始化版本（1.A） |
| `/api/v1/versions/items/{item_id}/history` | GET | 获取版本历史 |
| `/api/v1/versions/items/{item_id}/tree` | GET | 获取版本树 |
| `/api/v1/versions/{version_id}/revise` | POST | 创建新修订（A→B） |
| `/api/v1/versions/{version_id}/checkout` | POST | 检出版本（锁定） |
| `/api/v1/versions/{version_id}/checkin` | POST | 检入版本（解锁） |
| `/api/v1/versions/{version_id}/release` | POST | 发布版本 |
| `/api/v1/versions/{version_id}/iterations` | GET | 获取迭代列表 |
| `/api/v1/versions/{version_id}/iterations` | POST | 创建新迭代 |

### 23.4 修订方案（Revision Scheme）

系统支持多种修订方案：

| 方案 | 格式 | 示例序列 |
|------|------|----------|
| `letter` | A, B, C...Z, AA, AB | A → B → ... → Z → AA |
| `number` | 1, 2, 3... | 1 → 2 → 3 |
| `hybrid` | A1, A2...A9, B1 | A1 → A2 → ... → A9 → B1 |
| `semantic` | major.minor.patch | 1.0.0 → 1.0.1 → 1.1.0 |

### 23.5 手动验证版本 API

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 创建测试零件
PART_ID=$(curl -s http://127.0.0.1:7910/api/v1/aml/apply \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"type":"Part","action":"add","properties":{"item_number":"P-VER-001","name":"Version Test"}}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 初始化版本（得到 1.A）
VER_RESP=$(curl -s -X POST "http://127.0.0.1:7910/api/v1/versions/items/$PART_ID/init" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1')
VERSION_ID=$(echo $VER_RESP | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "Initial version: $(echo $VER_RESP | python3 -c 'import sys,json;print(json.load(sys.stdin)["version_label"])')"

# 创建修订（得到 1.B）
curl -s -X POST "http://127.0.0.1:7910/api/v1/versions/$VERSION_ID/revise" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"comment":"First revision"}'

# 查看版本历史
curl -s "http://127.0.0.1:7910/api/v1/versions/items/$PART_ID/history" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 查看版本树
curl -s "http://127.0.0.1:7910/api/v1/versions/items/$PART_ID/tree" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 24) S3 CAD Pipeline 验收脚本

### 24.1 一键验收：`scripts/verify_cad_pipeline_s3.sh`

此脚本验证 CAD Pipeline 在 S3 存储模式下的完整能力：

1. **文件上传**：上传 STL/GLB 等可视格式到 S3
2. **Job 触发**：`/cad/import` 创建 `cad_preview` 和 `cad_geometry` 任务
3. **Worker 处理**：Worker 从 S3 下载源文件、处理、上传产物回 S3
4. **预览/几何体获取**：`/file/{id}/preview` 和 `/file/{id}/geometry` 返回 302 重定向到 presigned URL

```bash
# 方式 A（推荐）：docker compose 一键启动（Postgres + MinIO + API + Worker）
docker compose up -d --build

# 可选：轻量启动（不启用 CAD Extractor）
docker compose -f docker-compose.yml -f docker-compose.no-cad-extractor.yml up -d --build

# 本地 CLI/worker 连接 docker Postgres + MinIO（用于脚本里的 seed/worker）
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL=http://localhost:59000
export YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000
export YUANTUS_S3_ACCESS_KEY_ID=minioadmin
export YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin

# 运行验收脚本
bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1

# 可选：自定义本地 CLI 路径
# CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_cad_pipeline_s3.sh ...
```

如果希望本地启动 API（不使用 compose 的 api/worker），至少需要先启动基础设施：

```bash
docker compose up -d postgres minio
```

期望输出：

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
OK: File uploaded: <file_id>
Preview job ID: <job_id>
Geometry job ID: <job_id>
==> Run worker to process jobs
OK: Worker executed
==> Check job statuses
Preview job status: completed
Geometry job status: completed
==> Check file metadata
Preview URL: /api/v1/file/<id>/preview
Geometry URL: /api/v1/file/<id>/geometry
Conversion status: completed
OK: Preview path set
OK: Geometry path set
==> Test preview endpoint
OK: Preview endpoint works (HTTP 302)
==> Test geometry endpoint
OK: Geometry endpoint works (HTTP 302)
==> Check storage type

---

## 24.2) CADGF Router 常驻（launchd）

> 适用于 macOS：CADGF Router 需要宿主机运行（包含 CADGF 原生插件/convert_cli）。

### 24.2.1 准备 CADGF 目录（避免 TCC/Downloads 限制）

```bash
mkdir -p /Users/huazhou/src
rsync -a /Users/huazhou/Downloads/Github/CADGameFusion/ /Users/huazhou/src/CADGameFusion-codex-yuantus/
```

### 24.2.2 配置 launchd plist

创建/更新：

```
~/Library/LaunchAgents/com.yuantus.cadgf-router.plist
```

内容（关键路径）：

```
/usr/bin/python3 /Users/huazhou/src/CADGameFusion-codex-yuantus/tools/plm_router_service.py
--host 127.0.0.1 --port 9000
--default-plugin /Users/huazhou/src/CADGameFusion-codex-yuantus/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib
--default-convert-cli /Users/huazhou/src/CADGameFusion-codex-yuantus/build_vcpkg/tools/convert_cli
```

### 24.2.3 启动/重载

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.yuantus.cadgf-router.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yuantus.cadgf-router.plist
launchctl kickstart -k gui/$(id -u)/com.yuantus.cadgf-router
```

### 24.2.4 健康检查

```bash
curl http://127.0.0.1:9000/health
```

期望：`status=ok`。

---

## 24.3) CADGF 在线预览（DWG/DXF）

> 说明：DWG 需要 ODAFileConverter，worker 必须在宿主机运行以调用 CADGF + ODA。

### 24.3.1 启动 host worker（临时）

```bash
docker compose stop worker

YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://127.0.0.1:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://127.0.0.1:59000' \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_CADGF_ROOT='/Users/huazhou/src/CADGameFusion-codex-yuantus' \
YUANTUS_CADGF_CONVERT_CLI='/Users/huazhou/src/CADGameFusion-codex-yuantus/build_vcpkg/tools/convert_cli' \
YUANTUS_CADGF_DXF_PLUGIN_PATH='/Users/huazhou/src/CADGameFusion-codex-yuantus/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib' \
YUANTUS_DWG_CONVERTER_BIN='/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter' \
.venv/bin/yuantus worker --poll-interval 2 --tenant tenant-1 --org org-1
```

### 24.3.2 执行在线预览验证

```bash
BASE_URL=http://127.0.0.1:7910 \
SAMPLE_FILE='/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg' \
scripts/verify_cad_preview_online.sh
```

### 24.3.3 恢复容器 worker

```bash
docker compose start worker
```
OK: S3 storage detected (302 redirect)
Testing S3 presigned URL follow (no API auth headers)...
OK: S3 presigned URL accessible (followed redirect)
==> Cleanup
OK: Cleaned up test file

==============================================
CAD Pipeline S3 Verification Complete
==============================================

ALL CHECKS PASSED
```

### 24.2 S3 存储模式数据流

```
┌─────────────┐    upload    ┌─────────────┐
│   Client    │ ─────────────▶│   API       │
└─────────────┘              └──────┬──────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │   MinIO/S3  │  (system_path = S3 key)
                             └──────┬──────┘
                                    │
                                    ▼
┌─────────────┐   download   ┌─────────────┐
│   Worker    │ ◀────────────│   MinIO/S3  │
└──────┬──────┘              └─────────────┘
       │ process
       ▼
┌─────────────┐    upload    ┌─────────────┐
│   Worker    │ ─────────────▶│   MinIO/S3  │  (preview_path, geometry_path = S3 keys)
└─────────────┘              └─────────────┘

                                    ▼
┌─────────────┐    302       ┌─────────────┐   presigned URL
│   Client    │ ◀────────────│   API       │ ────────────────▶ MinIO
└─────────────┘              └─────────────┘
```

### 24.3 关键配置

| 环境变量 | 说明 | 示例值 |
|----------|------|--------|
| `YUANTUS_STORAGE_TYPE` | 存储类型 | `s3` |
| `YUANTUS_S3_ENDPOINT_URL` | S3/MinIO 内部端点 | `http://minio:9000` |
| `YUANTUS_S3_PUBLIC_ENDPOINT_URL` | 客户端可访问端点 | `http://localhost:9000` |
| `YUANTUS_S3_BUCKET_NAME` | Bucket 名称 | `yuantus` |
| `YUANTUS_S3_ACCESS_KEY_ID` | 访问密钥 | `minioadmin` |
| `YUANTUS_S3_SECRET_ACCESS_KEY` | 访问密钥 | `minioadmin` |

### 24.4 Worker 侧 S3 处理流程

1. **下载源文件**：从 `system_path`（S3 key）下载到临时目录
2. **本地处理**：调用 CADConverterService 生成 preview/geometry
3. **上传产物**：将生成的文件上传到 S3（`previews/{id[:2]}/{id}.png`，`geometry/{id[:2]}/{id}.{format}`）
4. **更新记录**：将 S3 key 写入 `FileContainer.preview_path` / `geometry_path`
5. **清理临时文件**

### 24.5 API 侧 S3 响应

| 端点 | 本地存储 | S3 存储 |
|------|----------|---------|
| `GET /file/{id}/download` | `FileResponse` | `302 → presigned URL` |
| `GET /file/{id}/preview` | `FileResponse` | `302 → presigned URL` |
| `GET /file/{id}/geometry` | `FileResponse` | `302 → presigned URL` |

### 24.6 手动验证 S3 模式

```bash
# 设置 S3 环境变量
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL=http://localhost:9000

# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 创建测试 STL 文件
echo "solid test
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 1 0 0
vertex 0.5 1 0
endloop
endfacet
endsolid test" > /tmp/test.stl

# 上传并创建 Job
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/import \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F 'file=@/tmp/test.stl' \
  -F 'create_preview_job=true' \
  -F 'create_geometry_job=true'

# 运行 Worker
yuantus worker --worker-id w1 --poll-interval 1 --once

# 获取 geometry（应返回 302 重定向）
curl -v http://127.0.0.1:7910/api/v1/file/<FILE_ID>/geometry \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
# 期望: < HTTP/1.1 302 Found
# 期望: < location: http://localhost:9000/yuantus/...?X-Amz-Signature=...
```

---

## 25) CAD 2D Connectors 验收脚本（GStarCAD/ZWCAD/Haochen/Zhongwang）

### 25.1 一键验收：`scripts/verify_cad_connectors_2d.sh`

此脚本验证 DWG/DXF 文件通过 `/cad/import` 导入时可以用 `cad_format`（或 `cad_connector_id`）覆盖厂商标签，并支持基于文件内容/文件名的自动识别，且正确写入文件元数据：

- `cad_format` = `GSTARCAD` / `ZWCAD` / `HAOCHEN` / `ZHONGWANG`
- `cad_connector_id` = `gstarcad` / `zwcad` / `haochencad` / `zhongwangcad`
- `document_type` = `2d`
- `is_native_cad` = `true`
- `file_type` = `dwg` / `dxf`
- 自动识别：未传 `cad_format` 时仍能命中厂商 `cad_connector_id`

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1

# 可选：自定义 CLI/Python 路径
# CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_cad_connectors_2d.sh ...
```

期望输出：

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
OK: Created files: /tmp/yuantus_gstarcad_<ts>.dwg, /tmp/yuantus_zwcad_<ts>.dxf, /tmp/yuantus_haochencad_<ts>.dwg, /tmp/yuantus_zhongwang_<ts>.dxf, /tmp/yuantus_cad_auto_<ts>.dwg
==> Upload gstarcad_<ts>.dwg (GSTARCAD)
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (GSTARCAD)
==> Upload zwcad_<ts>.dxf (ZWCAD)
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (ZWCAD)
==> Upload haochencad_<ts>.dwg (HAOCHEN)
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (HAOCHEN)
==> Upload zhongwangcad_<ts>.dxf (ZHONGWANG)
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (ZHONGWANG)
==> Upload cad_auto_<ts>.dwg (auto-detect)
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (HAOCHEN)
==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 2D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
```

---

### 25.1.2 真实样本 + 连接器：`scripts/verify_cad_connectors_real_2d.sh`

用真实 DWG 文件验证 Haochen/Zhongwang 连接器覆盖，且 `cad_extract` 输出 `part_number/drawing_no`（来源于文件名解析或外部 extractor）。

可选环境变量：

- `CAD_SAMPLE_HAOCHEN_DWG`：浩辰样本 DWG 路径
- `CAD_SAMPLE_ZHONGWANG_DWG`：中望样本 DWG 路径
- `CAD_EXTRACTOR_BASE_URL`：外部 extractor 服务（可选）
- `CAD_REAL_FORCE_UNIQUE`：复制样本并追加标记字节以规避去重（默认 `1`）

```bash
export CAD_SAMPLE_HAOCHEN_DWG='/path/to/haochencad.dwg'
export CAD_SAMPLE_ZHONGWANG_DWG='/path/to/zhongwangcad.dwg'
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'

bash scripts/verify_cad_connectors_real_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

期望输出（摘要）：

```text
CAD 2D Real Connectors Verification Complete
ALL CHECKS PASSED
```

---

## 25.2) CAD 3D Connectors 验收脚本（SolidWorks/NX/Creo/CATIA/Inventor）

### 25.2.1 一键验收：`scripts/verify_cad_connectors_3d.sh`

此脚本验证 3D 文件通过 `/cad/import` 导入时可以正确解析 `cad_format`/`cad_connector_id`，并写入文件元数据：

- `cad_format` = `SOLIDWORKS` / `NX` / `CREO` / `CATIA` / `INVENTOR`
- `cad_connector_id` = `solidworks` / `nx` / `creo` / `catia` / `inventor`
- `document_type` = `3d`
- `is_native_cad` = `true`
- `file_type` = `sldprt` / `sldasm` / `prt` / `catpart` / `ipt`
- `.prt/.asm` 默认 NX，若需 Creo 请传 `cad_format=CREO` 或 `cad_connector_id=creo`

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_cad_connectors_3d.sh http://127.0.0.1:7910 tenant-1 org-1

# 可选：自定义 CLI/Python 路径
# CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_cad_connectors_3d.sh ...
```

期望输出：

```text
==============================================
CAD 3D Connectors Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta
==> Login as admin
OK: Admin login
==> Create dummy 3D files
OK: Created files
==> Upload solidworks_part_<ts>.sldprt
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (SOLIDWORKS)
==> Upload nx_<ts>.prt
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (NX)
==> Upload creo_<ts>.prt
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (CREO)
==> Upload catia_<ts>.catpart
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (CATIA)
==> Upload inventor_<ts>.ipt
OK: Uploaded file: <file_id>
Metadata OK
OK: Metadata verified (INVENTOR)
==> Cleanup
OK: Cleaned up temp files

==============================================
CAD 3D Connectors Verification Complete
==============================================
ALL CHECKS PASSED
```

---

## 26) 一键回归测试：`scripts/verify_all.sh`

### 26.1 概述

`scripts/verify_all.sh` 是 YuantusPLM 的端到端回归测试总入口，依次调用所有验收脚本并汇总结果。

### 26.1.1 Python 版本要求

建议使用 Python 3.10+（推荐 3.11）。若存在旧版 `.venv`，可按以下方式重建：

```bash
python3.11 -m venv --clear .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -e .
```

升级后建议执行一次全量回归：

```bash
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 26.2 运行方式

```bash
# 启动服务（推荐 docker compose）
docker compose up -d --build

# 或本地启动
yuantus start --port 7910 &

# 运行一键回归（使用默认参数）
bash scripts/verify_all.sh

# 或指定参数
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1

# Docker/Postgres 环境可指定 DB_URL（CLI seed 与 API 同库）
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1

# 自定义 CLI/Python 路径
CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_all.sh
```

### 26.3 测试套件

| 测试名称 | 脚本 | 验证内容 |
|----------|------|----------|
| Run H (Core APIs) | `verify_run_h.sh` | Health、AML、Search、RPC、File、BOM |
| S2 (Documents & Files) | `verify_documents.sh` | 文件元数据、去重、挂载列表 |
| S1 (Meta + RBAC) | `verify_permissions.sh` | 权限配置、RBAC 执行 |
| S3.1 (BOM Tree) | `verify_bom_tree.sh` | BOM 写入、循环检测 |
| S3.2 (BOM Effectivity) | `verify_bom_effectivity.sh` | 生效性过滤 |
| S3.3 (Versions) | `verify_versions.sh` | 版本初始化、修订、迭代 |
| S4 (ECO Advanced) | `verify_eco_advanced.sh` | Impact 分析、BOM Redline、批量审批 |
| S5-A (CAD Pipeline S3) | `verify_cad_pipeline_s3.sh` | S3 存储、Worker 处理 |
| S5-B (CAD 2D Connectors) | `verify_cad_connectors_2d.sh` | DWG/DXF 厂商标签覆盖 |
| S5-B (CAD 2D Real Connectors) | `verify_cad_connectors_real_2d.sh` | 真实 DWG + 连接器覆盖验证 |
| S5-B (CAD 2D Connector Coverage) | `verify_cad_connector_coverage_2d.sh` | 离线 DWG 覆盖率统计（Haochen/Zhongwang） |
| S5-B (CAD 3D Connectors) | `verify_cad_connectors_3d.sh` | 3D 连接器识别（SOLIDWORKS/NX/CREO/CATIA/INVENTOR） |
| S5-C (CAD Attribute Sync) | `verify_cad_sync.sh` | x-cad-synced 属性同步 |
| S5-B (CAD Connectors Config) | `verify_cad_connectors_config.sh` | 自定义连接器配置 reload |
| S5-C (CAD Sync Template) | `verify_cad_sync_template.sh` | CAD 属性映射模板导入/导出 |
| S5-C (CAD Auto Part) | `verify_cad_auto_part.sh` | 导入时自动创建 Part + 附件绑定 |
| S5-C (CAD Extractor Stub) | `verify_cad_extractor_stub.sh` | 外部提取服务对接（stub） |
| S5-C (CAD Extractor Service) | `verify_cad_extractor_service.sh` | 外部提取服务（microservice） |
| CAD Real Samples | `verify_cad_real_samples.sh` | 真实 DWG/STEP/PRT 端到端 |
| S6 (Search Index) | `verify_search_index.sh` | 搜索索引增量刷新 |
| S6 (Search Reindex) | `verify_search_reindex.sh` | 搜索索引状态 + 全量重建 |
| S6 (Search ECO) | `verify_search_eco.sh` | ECO 搜索（ES/DB fallback） |
| S6 (Reports Summary) | `verify_reports_summary.sh` | 聚合报表统计 |
| Audit Logs | `verify_audit_logs.sh` | 审计日志查询（需启用 AUDIT_ENABLED） |
| S8 (Ops Monitoring) | `verify_ops_s8.sh` | 配额监控/审计留存/报表元信息 |
| S7 (Multi-Tenancy) | `verify_multitenancy.sh` | 租户/组织隔离（按 TENANCY_MODE） |
| S7 (Deep Verification) | `verify_s7.sh` / `run_s7_deep.sh` | 多租户 + 配额 + 审计 + 运维 + 搜索 + 租户开通 |
| S7 (Tenant Provisioning) | `verify_tenant_provisioning.sh` | 平台管理员创建 tenant/org |
| Where-Used API | `verify_where_used.sh` | 反向 BOM 查询 |
| BOM Compare | `verify_bom_compare.sh` | BOM 差异对比（如端点可用则执行） |
| BOM Substitutes | `verify_substitutes.sh` | BOM 替代件管理（如端点可用则执行） |
| MBOM Convert | `verify_mbom_convert.sh` | EBOM → MBOM 转换 |
| Item Equivalents | `verify_equivalents.sh` | Part 等效件管理（如端点可用则执行） |
| Version-File Binding | `verify_version_files.sh` | 版本-文件绑定（如端点可用则执行） |

> 说明：`S7 (Multi-Tenancy)` 仅在 `TENANCY_MODE=db-per-tenant` 或 `db-per-tenant-org` 时执行；单租户模式会显示 `SKIP`。
> `S7 (Deep Verification)` 建议使用 `scripts/run_s7_deep.sh`，它会为 Docker 环境自动设置 `DB_URL/DB_URL_TEMPLATE/IDENTITY_DB_URL` 并校验 `tenancy_mode`。
> 若需要自动判断可运行的可选模块（CAD/Extractor/UI 聚合等），使用 `scripts/run_integration_stable.sh`（见 `docs/INTEGRATION_ENV_GUIDE_20260127.md`）。
> `S5-C (CAD Extractor Stub)` 需要设置 `RUN_CAD_EXTRACTOR_STUB=1` 才会执行。
> `S5-C (CAD Extractor Service)` 需要设置 `RUN_CAD_EXTRACTOR_SERVICE=1` 才会执行。
> `S5-C (CAD Auto Part)` 需要设置 `RUN_CAD_AUTO_PART=1` 才会执行。
> `CAD Real Samples` 需要设置 `RUN_CAD_REAL_SAMPLES=1` 才会执行。
> `S5-B (CAD 2D Real Connectors)` 需要设置 `RUN_CAD_REAL_CONNECTORS_2D=1` 才会执行。
> `S5-B (CAD 2D Connector Coverage)` 需要设置 `RUN_CAD_CONNECTOR_COVERAGE_2D=1` 且 `CAD_CONNECTOR_COVERAGE_DIR=/path/to/dwg`。
> `S7 (Tenant Provisioning)` 需要设置 `RUN_TENANT_PROVISIONING=1` 且 `YUANTUS_PLATFORM_ADMIN_ENABLED=true`。
> `S8 (Ops Monitoring)` 需要设置 `RUN_OPS_S8=1` 且启用 `YUANTUS_PLATFORM_ADMIN_ENABLED=true`、`YUANTUS_AUDIT_ENABLED=true`、`YUANTUS_QUOTA_MODE=enforce`。
> UI 聚合验收需要设置 `RUN_UI_AGG=1`（涵盖产品详情、BOM UI、文档/审批摘要）。

### 26.4 输出格式

```text
==============================================
YuantusPLM End-to-End Regression Suite
==============================================
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
CLI: .venv/bin/yuantus
==============================================

==> Pre-flight checks
CLI: OK
Python: OK
API Health: OK (HTTP 200)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: Run H (Core APIs)
Script: scripts/verify_run_h.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...
PASS: Run H (Core APIs)

如在本机运行且服务使用容器内数据库（host 名为 `postgres`），可通过环境变量覆盖：

```bash
TENANCY_MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
ATHENA_AUTH_TOKEN='<athena_token>' \
  bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: S1 (Meta + RBAC)
...

==============================================
REGRESSION TEST SUMMARY
==============================================

Test Suite                Result
------------------------- ------
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

----------------------------------------------
PASS: 13  FAIL: 0  SKIP: 1
----------------------------------------------

ALL TESTS PASSED
```

### 26.5 CI 运行建议

默认 CI 使用 `docker compose` 启动全套服务（Postgres + MinIO + CAD Extractor），并开启 CAD 自动建件与 Extractor 校验：

```bash
docker compose -p yuantusplm up -d --build

RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

如果 CI 资源受限，可切换为本地存储 + 单库模式（跳过 CAD Extractor 服务）：

```bash
export YUANTUS_STORAGE_TYPE=local
export YUANTUS_TENANCY_MODE=single
export YUANTUS_SCHEMA_MODE=migrations

bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 26.6 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 所有测试通过 |
| 1 | 有测试失败 |
| 2 | 预检失败（CLI/Python 不存在或 API 不可达） |

---

## 27) Where-Used API 验收脚本

### 27.1 一键验收：`scripts/verify_where_used.sh`

此脚本验证 BOM Where-Used（反向查询）的完整能力：

1. **非递归查询**：查询直接父件列表
2. **递归查询**：查询所有祖先（含层级）
3. **空结果处理**：顶层 Item 返回空列表
4. **404 处理**：不存在的 Item 返回 404

```bash
# 启动服务
yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1

# 或自定义 CLI/Python 路径
CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_where_used.sh
```

期望输出：

```text
==============================================
Where-Used API Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity (admin user)
OK: Identity seeded
==> Seed meta schema
OK: Meta schema seeded
==> Login as admin
OK: Admin login
==> Create test items for BOM hierarchy
OK: Created assembly: ...
OK: Created sub-assembly: ...
OK: Created component: ...
OK: Created second assembly: ...
==> Build BOM hierarchy
OK: Added sub-assembly to assembly
OK: Added component to sub-assembly
OK: Added component to second assembly

BOM Structure:
  ASSEMBLY (...)
    └── SUB-ASSEMBLY (...)
          └── COMPONENT (...)
  ASSEMBLY2 (...)
    └── COMPONENT (...)

==> Test Where-Used (non-recursive)
Where-used response:
  item_id: ...
  count: 2
OK: Non-recursive where-used: found 2 direct parents

==> Test Where-Used (recursive)
Recursive where-used response:
  count: 3
OK: Recursive where-used: found 3 parents
Parents by level:
  Level 1: Sub-Assembly for Where-Used Test
  Level 1: Second Assembly for Where-Used Test
  Level 2: Assembly for Where-Used Test

==> Test Where-Used on top-level item (no parents)
OK: Top-level item has no parents (count=0)

==> Test Where-Used on non-existent item
OK: Non-existent item returns 404 (HTTP 404)

==============================================
Where-Used API Verification Complete
==============================================

Summary:
  - BOM hierarchy creation: OK
  - Non-recursive where-used: OK (found 2 direct parents)
  - Recursive where-used: OK (found 3 total parents)
  - Top-level item (no parents): OK
  - Non-existent item handling: OK (404)

ALL CHECKS PASSED
```

### 27.2 Where-Used API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/bom/{item_id}/where-used` | GET | 查询哪些父件使用了此 Item |

### 27.3 请求参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `recursive` | bool | `false` | 是否递归查询祖先 |
| `max_levels` | int | `10` | 递归查询的最大深度 |

### 27.4 响应格式

```json
{
  "item_id": "component-uuid",
  "count": 3,
  "parents": [
    {
      "relationship": {
        "id": "bom-relationship-uuid",
        "item_type_id": "Part BOM",
        "quantity": 2,
        "uom": "EA"
      },
      "parent": {
        "id": "parent-uuid",
        "item_number": "ASSY-001",
        "name": "Assembly"
      },
      "level": 1
    },
    {
      "relationship": {...},
      "parent": {...},
      "level": 2
    }
  ]
}
```

### 27.5 使用场景

| 场景 | 说明 |
|------|------|
| **影响分析** | "如果修改这个零件，哪些装配体会受影响？" |
| **合规追溯** | "这个有问题的组件被用在了哪些产品中？" |
| **成本汇总** | "包含这个零件的装配体有哪些？" |
| **变更评估** | "ECO 影响范围有多大？" |

### 27.6 手动验证 Where-Used API

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 查询 Where-Used（非递归）
curl -s "http://127.0.0.1:7910/api/v1/bom/<COMPONENT_ID>/where-used" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 查询 Where-Used（递归，最多 5 层）
curl -s "http://127.0.0.1:7910/api/v1/bom/<COMPONENT_ID>/where-used?recursive=true&max_levels=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 28) BOM Compare 验收脚本

### 28.1 一键验收：`scripts/verify_bom_compare.sh`

此脚本验证 BOM Compare 的核心能力：

1. **新增/删除差异**：左右 BOM 结构不同
2. **属性差异**：quantity/uom/find_num/refdes 变化
3. **输出结构**：summary + added/removed/changed
4. **字段级差异**：changed[*].changes + severity + summary.changed_major
5. **compare_mode**：only_product（只存在性）/ num_qty（数量进 line_key）

```bash
# 启动服务
yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1

# 或自定义 CLI/Python 路径
CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_bom_compare.sh
```

期望输出：

```text
==============================================
BOM Compare Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta
==> Login as admin
OK: Admin login
==> Create parent items
OK: Created parents: A=..., B=...
==> Create child items
OK: Created children: X=..., Y=..., Z=...
==> Build BOM A (baseline)
OK: BOM A created
==> Build BOM B (changed + added)
OK: BOM B created
==> Compare BOM
BOM Compare: OK

==============================================
BOM Compare Verification Complete
==============================================
ALL CHECKS PASSED
```

### 28.2 字段级对照清单（BOM Compare）

#### 28.2.1 Line Key（对齐策略）

| `line_key` | 组成 | 适用场景 | 说明 |
|---|---|---|---|
| `child_config` | `parent_config_id + child_config_id` | 默认 | 与历史行为一致，适合一条子件只有一行 |
| `child_id` | `parent_id + child_id` | 版本对齐 | 忽略 config 变化，适合跨版本对比 |
| `relationship_id` | `relationship_id` | 精确对齐 | 只用于同一 BOM 行 ID 对比 |
| `child_config_find_num` | `child_config_id + find_num` | 版本对齐 + 序号 | 同一子件多行、find_num 不同 |
| `child_config_refdes` | `child_config_id + refdes` | 版本对齐 + 位号 | 同一子件多行、refdes 不同 |
| `child_config_find_refdes` | `child_config_id + find_num + refdes` | 版本对齐 + 组合区分 | find_num/refdes 组合 |
| `child_config_find_num_qty` | `child_config_id + find_num + quantity` | 版本对齐 + 数量 | 数量变化视为新增/删除 |
| `child_id_find_num` | `child_id + find_num` | 序号区分 | 同一子件多行、find_num 不同 |
| `child_id_refdes` | `child_id + refdes` | 位号区分 | 同一子件多行、refdes 不同 |
| `child_id_find_refdes` | `child_id + find_num + refdes` | 组合区分 | find_num/refdes 组合 |
| `child_id_find_num_qty` | `child_id + find_num + quantity` | 数量敏感 | 数量变化视为新增/删除 |
| `line_full` | `child_id + find_num + refdes + effectivity` | 生效区分 | 生效窗口不同视为不同 BOM 行 |

> 注意：`line_full` 会把 find_num/refdes/effectivity 的变化判定为新增/删除，而非字段级变更。

#### 28.2.7 compare_mode（结构对齐规则）

| `compare_mode` | 默认 `line_key` | 属性比较 | 说明 |
|---|---|---|---|
| `only_product` | `child_config` | 无 | 只比较存在性（不比较数量/位号） |
| `summarized` | `child_config` | `quantity`, `uom` | 汇总同一子件的数量后对比 |
| `num_qty` | `child_config_find_num_qty` | `quantity`, `uom`, `find_num` | 数量变化视为新增/删除 |
| `by_position` | `child_config_find_num` | `quantity`, `uom`, `find_num` | 按序号对齐 |
| `by_reference` | `child_config_refdes` | `quantity`, `uom`, `refdes` | 按位号对齐 |

> 规则：`compare_mode` 会覆盖 `line_key` 与 `include_relationship_props` 的默认策略（若需要自定义，请直接传 `line_key`）。

#### 28.2.2 关系属性字段对照（BOM 行属性）

| 字段 | 含义 | 来源 | 规范化 | 严重度 | 说明 |
|---|---|---|---|---|---|
| `quantity` | 用量 | `properties` | `Decimal/float` | `major` | 数量变化影响物料需求 |
| `uom` | 单位 | `properties` | `upper().strip()` | `major` | 单位变化影响换算 |
| `find_num` | 序号 | `properties` | `strip()` | `minor` | 工艺装配序号 |
| `refdes` | 位号 | `properties` | 分隔/去重/排序/大写 | `minor` | 位号变化影响装配说明 |
| `effectivity_from` | 生效起始 | `properties` | ISO → string | `major` | 生效窗口变化影响结构 |
| `effectivity_to` | 生效结束 | `properties` | ISO → string | `major` | 生效窗口变化影响结构 |
| `effectivities` | 生效记录 | `meta_effectivities` | list 归一化 | `major` | 需 `include_effectivity=true` |
| `substitutes` | 替代件 | `Part BOM Substitute` | list 归一化 | `minor` | 需 `include_substitutes=true` |
| 其他字段 | 扩展属性 | `properties` | 原样/白名单 | `info` | 仅在 include_relationship_props 时比较 |

> 规则：`changed[*].severity` 取字段级变更中最高严重度；summary 统计 `changed_major/minor/info`。

#### 28.2.3 结构/路径字段（返回值）

| 字段 | 含义 | 说明 |
|---|---|---|
| `relationship_id` | BOM 行 ID | 关系对象的 `id` |
| `line_key` | 对齐 key | 由 `line_key` 策略生成 |
| `parent_config_id` | 父对象配置 ID | Master/Config ID |
| `child_config_id` | 子对象配置 ID | Master/Config ID |
| `level` | 深度 | 根子件为 `1` |
| `path` | 路径 | `{id, config_id, item_number, name}` 列表 |
| `parent`/`child` | 父/子字段 | 需 `include_child_fields=true` |

#### 28.2.4 子件字段对照（include_child_fields=true）

| 字段 | 来源 | 说明 |
|---|---|---|
| `parent.id` | `meta_items.id` | 父件 ID |
| `parent.config_id` | `meta_items.config_id` | 父件配置 ID |
| `parent.item_number` | `meta_items.properties.item_number` | 父件物料号 |
| `parent.name` | `meta_items.properties.name` | 父件名称 |
| `child.id` | `meta_items.id` | 子件 ID |
| `child.config_id` | `meta_items.config_id` | 子件配置 ID |
| `child.item_number` | `meta_items.properties.item_number` | 子件物料号 |
| `child.name` | `meta_items.properties.name` | 子件名称 |

#### 28.2.5 替代件字段对照（include_substitutes=true）

| 字段 | 来源 | 说明 |
|---|---|---|
| `substitutes[].item_id` | `meta_items.id` | 替代件 ID |
| `substitutes[].rank` | 关系属性 | 替代优先级 |
| `substitutes[].note` | 关系属性 | 备注 |

#### 28.2.6 生效性字段对照（include_effectivity=true）

| 字段 | 来源 | 说明 |
|---|---|---|
| `effectivities[].type` | `meta_effectivities.effectivity_type` | 生效类型 |
| `effectivities[].start_date` | `meta_effectivities.start_date` | 起始日期（ISO） |
| `effectivities[].end_date` | `meta_effectivities.end_date` | 结束日期（ISO） |
| `effectivities[].payload` | `meta_effectivities.payload` | 扩展数据 |

### 28.3 手动验证 BOM Compare

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Compare (item 维度)
curl -s "http://127.0.0.1:7910/api/v1/bom/compare?left_type=item&left_id=<LEFT_ID>&right_type=item&right_id=<RIGHT_ID>&max_levels=10&line_key=child_id&include_relationship_props=quantity,uom,find_num,refdes,effectivity_from,effectivity_to&include_substitutes=true&include_effectivity=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# Compare with compare_mode (示例：only_product)
curl -s "http://127.0.0.1:7910/api/v1/bom/compare?left_type=item&left_id=<LEFT_ID>&right_type=item&right_id=<RIGHT_ID>&max_levels=10&compare_mode=only_product" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 29) BOM Substitutes 验收脚本

### 29.1 一键验收：`scripts/verify_substitutes.sh`

此脚本验证 BOM 替代件的完整能力：

1. **新增替代件**：对 BOM 行添加 Substitute
2. **列表查询**：获取 BOM 行的所有替代件
3. **重复保护**：同 BOM 行 + 同替代件禁止重复
4. **删除替代件**：删除指定 Substitute

```bash
# 启动服务
yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_substitutes.sh http://127.0.0.1:7910 tenant-1 org-1

# 或自定义 CLI/Python 路径
CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_substitutes.sh
```

期望输出：

```text
==============================================
BOM Substitutes Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta
==> Login as admin
OK: Admin login
==> Create parent/child/substitute items
OK: Created parent=... child=... substitutes=..., ...
==> Create BOM line (parent -> child)
OK: Created BOM line: ...
==> Add substitute 1
OK: Added substitute 1: ...
==> List substitutes (expect 1)
OK: List count=1
==> Add substitute 2
OK: Added substitute 2: ...
==> Duplicate add (should 400)
OK: Duplicate add blocked (400)
==> Remove substitute 1
OK: Removed substitute 1
==> List substitutes (expect 1 remaining)
OK: List count=1 after delete

==============================================
BOM Substitutes Verification Complete
==============================================
ALL CHECKS PASSED
```

### 29.2 手动验证 BOM Substitutes

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 添加 substitute
curl -s -X POST "http://127.0.0.1:7910/api/v1/bom/<BOM_LINE_ID>/substitutes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"substitute_item_id":"<SUB_PART_ID>","properties":{"rank":1,"note":"alt"}}'

# 查询 substitutes
curl -s "http://127.0.0.1:7910/api/v1/bom/<BOM_LINE_ID>/substitutes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 删除 substitute
curl -s -X DELETE "http://127.0.0.1:7910/api/v1/bom/<BOM_LINE_ID>/substitutes/<SUB_REL_ID>" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 30) Version-File Binding 验收脚本

### 30.1 一键验收：`scripts/verify_version_files.sh`

此脚本验证版本‑文件绑定与锁定逻辑：

1. **Checkout 锁定**：他人无法修改 item 文件关联
2. **Checkin 同步**：item 文件自动同步到 VersionFile
3. **Version 文件查询**：/versions/{id}/files 返回正确角色
4. **Version 文件编辑**：仅允许 checkout 持有者修改（attach/detach/primary/thumbnail）

```bash
# 启动服务
yuantus start --port 7910 &

# 运行验收脚本
bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1

# 或自定义 CLI/Python 路径
CLI=.venv/bin/yuantus PY=.venv/bin/python bash scripts/verify_version_files.sh
```

期望输出：

```text
==============================================
Version-File Binding Verification
BASE_URL: http://127.0.0.1:7910
TENANT: tenant-1, ORG: org-1
==============================================

==> Seed identity/meta
OK: Seeded identity/meta
==> Login as admin
OK: Admin login
==> Login as viewer
OK: Viewer login
==> Create Part item
OK: Created Part: ...
==> Init version
OK: Init version: ...
==> Upload file
OK: Uploaded file: ...
==> Attach file to item (native_cad)
OK: File attached to item
==> Checkout version (lock files)
OK: Checked out version
==> Viewer attach should be blocked (409)
OK: Attach blocked for non-owner
==> Checkin version (sync files)
OK: Checked in version
==> Verify version files
Version files synced: OK

==============================================
Version-File Binding Verification Complete
==============================================
ALL CHECKS PASSED
```

### 30.2 手动验证 Version-File Binding

```bash
# 获取 admin token
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 创建 Part + init version 后上传文件
curl -s -X POST "http://127.0.0.1:7910/api/v1/file/upload" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -F "file=@/tmp/test.txt;filename=test.txt"

# 关联到 item
curl -s -X POST "http://127.0.0.1:7910/api/v1/file/attach" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"item_id":"<ITEM_ID>","file_id":"<FILE_ID>","file_role":"native_cad"}'

# checkout 锁定
curl -s -X POST "http://127.0.0.1:7910/api/v1/versions/items/<ITEM_ID>/checkout" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"comment":"lock files"}'

# checkin 同步
curl -s -X POST "http://127.0.0.1:7910/api/v1/versions/items/<ITEM_ID>/checkin" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"comment":"sync files"}'

# 查询版本文件
curl -s "http://127.0.0.1:7910/api/v1/versions/<VERSION_ID>/files" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 31) S4 ECO Advanced 验收脚本

### 31.1 一键验收：`scripts/verify_eco_advanced.sh`

```bash
bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1

# Docker/Postgres 环境可指定 DB_URL（CLI seed 与 API 同库）
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

验证内容：

- ECO Impact 分析（where-used + files 汇总 + bom_diff 明细 + version diff）
- ECO Impact 导出（CSV/XLSX/PDF）
- ECO BOM Redline（source vs target 版本差异）
- ECO BOM Redline compare_mode（only_product）
- ECO 导出元信息（compare_mode/line_key）
- 批量审批（admin 成功，viewer 拒绝 + summary 统计）
- SLA 逾期提醒（overdue 列表 + notify 触发）

### 31.2 关键 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/eco/{eco_id}/impact` | GET | ECO Impact 分析（支持 `compare_mode`、`include_files`、`include_bom_diff`、`include_version_diff`、`max_levels`） |
| `/api/v1/eco/{eco_id}/impact/export` | GET | ECO Impact 导出（`format=csv|xlsx|pdf|json`） |
| `/api/v1/eco/{eco_id}/bom-diff` | GET | ECO 源/目标版本 BOM Redline（支持 `compare_mode`） |
| `/api/v1/eco/approvals/batch` | POST | 批量审批/拒绝 |
| `/api/v1/eco/approvals/overdue` | GET | SLA 逾期列表 |
| `/api/v1/eco/approvals/notify-overdue` | POST | 触发 SLA 逾期提醒 |

### 31.3 手动验证示例

```bash
# 1) Impact (include BOM + version diff)
curl -s "http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/impact?include_files=true&include_bom_diff=true&include_version_diff=true&max_levels=5&include_relationship_props=quantity" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 1.1) Impact Export (CSV/XLSX/PDF)
curl -s -o /tmp/eco_impact.csv \
  "http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/impact/export?format=csv&include_files=true&include_bom_diff=true&include_version_diff=true&compare_mode=only_product" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

curl -s -o /tmp/eco_impact.xlsx \
  "http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/impact/export?format=xlsx&include_files=true&include_bom_diff=true&include_version_diff=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

curl -s -o /tmp/eco_impact.pdf \
  "http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/impact/export?format=pdf&include_files=true&include_bom_diff=true&include_version_diff=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 2) BOM Redline
curl -s "http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/bom-diff?max_levels=5&include_relationship_props=quantity,uom" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 2.1) BOM Redline (compare_mode=only_product)
curl -s "http://127.0.0.1:7910/api/v1/eco/<ECO_ID>/bom-diff?max_levels=5&compare_mode=only_product" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 3) Batch approvals
curl -s -X POST "http://127.0.0.1:7910/api/v1/eco/approvals/batch" \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"eco_ids":["<ECO_ID_1>","<ECO_ID_2>"],"mode":"approve","comment":"batch approve"}'

# 4) SLA overdue + notify
curl -s "http://127.0.0.1:7910/api/v1/eco/approvals/overdue" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

curl -s -X POST "http://127.0.0.1:7910/api/v1/eco/approvals/notify-overdue" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

---

## 32) S7 多租户隔离验收脚本

### 32.0 一键深度验收（推荐）

```bash
# 推荐：自动设置 DB_URL / DB_URL_TEMPLATE / IDENTITY_DB_URL 并校验 tenancy_mode
scripts/run_s7_deep.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

### 32.1 一键验收：`scripts/verify_multitenancy.sh`

> 该脚本要求服务以 `TENANCY_MODE=db-per-tenant` 或 `db-per-tenant-org` 启动。

```bash
# 示例（SQLite，db-per-tenant-org）
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL=sqlite:///yuantus_mt.db
export YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_identity_mt.db
yuantus start --port 7912 &

bash scripts/verify_multitenancy.sh http://127.0.0.1:7912 tenant-1 tenant-2 org-1 org-2
```

### 32.2 Postgres 模板模式示例

```bash
# Docker Compose 覆盖（自动创建租户/组织数据库）
docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build
bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2

# 先准备租户/组织数据库
./scripts/mt_pg_bootstrap.sh
#
# 如需重置（schema 变更时，谨慎使用）
RESET=1 ./scripts/mt_pg_bootstrap.sh

# 通过 DATABASE_URL_TEMPLATE 指定每租户/组织的数据库
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
yuantus start --port 7912 &

DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
bash scripts/verify_multitenancy.sh http://127.0.0.1:7912 tenant-1 tenant-2 org-1 org-2
```

### 32.3 验证内容

- Tenant A 创建的数据不可被 Tenant B 访问
- 同一 Tenant 下不同 Org 数据互相隔离（db-per-tenant-org）
- 通过 `x-tenant-id` / `x-org-id` 切换上下文

### 32.4 多租户迁移脚本：`scripts/mt_migrate.sh`

该脚本用于 db-per-tenant / db-per-tenant-org 场景下批量执行 Alembic 迁移。

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

TENANTS=tenant-1,tenant-2 ORGS=org-1,org-2 \
  ./scripts/mt_migrate.sh
```

如需禁用自动 stamp（已有表且无 alembic_version 时），可设置：

```bash
AUTO_STAMP=0 ./scripts/mt_migrate.sh
```

当数据库已有表但缺少 `alembic_version`（例如 `create_all` 创建），
脚本默认先 stamp 到初始版本再执行 upgrade。可通过 `AUTO_STAMP_REVISION` 覆盖默认初始 revision：

```bash
AUTO_STAMP_REVISION=f87ce5711ce1 ./scripts/mt_migrate.sh
```

---

## 33) CAD Attribute Sync（x-cad-synced）验收脚本

### 33.1 一键验收：`scripts/verify_cad_sync.sh`

该脚本验证 CAD 属性只写入标记为 `is_cad_synced` 的字段，并支持 `ui_options.cad_key` 自定义映射。
流程使用 `/cad/import` 创建 `cad_extract` 任务，并将抽取结果同步到 Item，同时将抽取结果
持久化到 `meta_files.cad_attributes`，可通过 `GET /cad/files/{file_id}/attributes` 回读。

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1

# 若使用 docker compose (MinIO/S3)，请补充：
# export YUANTUS_STORAGE_TYPE=s3
# export YUANTUS_S3_ENDPOINT_URL=http://localhost:59000
# export YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000
```

### 33.2 验证内容

- `item_number` 通过 `cad_key=part_number` 更新为 `HC-001`
- `description` 使用默认映射更新为 `浩辰CAD零件`
- `name` 不受 CAD 同步影响
- 未标记字段（如 `material`）不会写入
- `cad_extract` 回读返回 `part_number=HC-001`

### 33.3 真实 DWG + 外部 Extractor（可选）

使用真实 DWG 时，可通过环境变量覆盖样例文件与期望值，并指向外部 Extractor：

```bash
export YUANTUS_CAD_EXTRACTOR_BASE_URL='http://127.0.0.1:8200'
export CAD_SYNC_SAMPLE_FILE='/path/to/sample.dwg'
export CAD_SYNC_EXPECT_ITEM_NUMBER='ABC-001'
export CAD_SYNC_EXPECT_DESCRIPTION='零件名称'
export CAD_SYNC_EXPECT_REVISION='v2'   # 可选
export CAD_SYNC_CAD_FORMAT='AUTOCAD'   # 可选
export CAD_SYNC_CONNECTOR_ID='autocad' # 可选

bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

### 33.4 CAD Auto Part（导入自动建 Part）

`/cad/import` 支持 `auto_create_part=true`，当未提供 `item_id` 时自动创建 Part 并绑定附件。

```bash
export CAD_AUTO_SAMPLE_FILE='/path/to/sample.dwg'
export CAD_AUTO_EXPECT_ITEM_NUMBER='ABC-001'
export CAD_AUTO_EXPECT_DESCRIPTION='零件名称'
# 可选：
export CAD_AUTO_EXPECT_REVISION='v2'
export CAD_AUTO_CAD_FORMAT='AUTOCAD'
export CAD_AUTO_CONNECTOR_ID='autocad'

RUN_CAD_AUTO_PART=1 \
  bash scripts/verify_cad_auto_part.sh http://127.0.0.1:7910 tenant-1 org-1
```

验证点：

- 自动创建/复用 Part（`item_id` 返回）
- `item_number/description` 写入 Part 属性
- 文件附件绑定成功（`/file/item/{item_id}`）

---

## 34) Search Index 验收脚本

### 34.1 一键验收：`scripts/verify_search_index.sh`

该脚本验证搜索索引在新增/更新/删除后可正确检索。

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_search_index.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 34.2 验证内容

- 新增 Part 后可按 `item_number` 检索到
- 更新 `name` 后可按新名称检索到
- 删除后不再被检索到

---

### 34.3 Search ECO 验证

该脚本验证 `/search/ecos` 支持按名称/状态检索 ECO（管理员接口）。当启用 ES/OpenSearch 时，会先调用 `/search/ecos/status` 和 `/search/ecos/reindex`。

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_search_eco.sh http://127.0.0.1:7910 tenant-1 org-1
```

验证点：

- `/search/ecos/status` 返回引擎与索引状态（如启用 ES/OS）
- `/search/ecos/reindex` 成功（如启用 ES/OS）
- 创建 ECO 后可按 `name` 检索到
- `state=draft` 过滤可返回目标 ECO

---

## 35) Reports Summary 验收脚本

### 35.1 一键验收：`scripts/verify_reports_summary.sh`

该脚本验证 `/reports/summary` 输出聚合统计信息。

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_reports_summary.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 35.2 验证内容

- Items: `total` 与 `by_type` 包含 Part
- Files: `by_document_type` 包含 `other`
- ECO: `by_state` 包含 `draft`
- Jobs: `by_status` 包含 `pending`

---

## 36) Audit Logs 验收脚本

### 36.1 一键验收：`scripts/verify_audit_logs.sh`

该脚本验证 `/admin/audit` 输出审计日志。运行前需确保：

- `YUANTUS_AUDIT_ENABLED=true`
- API 已重启加载配置

```bash
export YUANTUS_AUDIT_ENABLED=true
docker compose up -d --build

DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 36.2 验证内容

- 调用 `/api/v1/health` 后产生审计记录
- `/api/v1/admin/audit` 可按 `path` 查询到记录

### 36.3 Retention 验证（可选）

如需验证保留策略，请在启动服务前设置：

```bash
export YUANTUS_AUDIT_RETENTION_MAX_ROWS=5
export YUANTUS_AUDIT_RETENTION_DAYS=1
export YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1
```

然后运行：

```bash
VERIFY_RETENTION=1 \
  DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

验证内容：

- 记录总数不超过 `AUDIT_RETENTION_MAX_ROWS`
- 过期时间前的日志会被清理

---

## 37) Ops Health 验收脚本

### 37.1 一键验收：`scripts/verify_ops_health.sh`

该脚本验证 `/api/v1/health/deps` 返回 DB、Identity DB、Storage 依赖健康状态。

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_ops_health.sh http://127.0.0.1:7910 tenant-1 org-1
```

如需同时验证 `/api/v1/integrations/health`（并为 Athena 传独立 token），可执行：

```bash
CHECK_INTEGRATIONS=1 \
  ATHENA_AUTH_TOKEN='<athena_token>' \
  YUANTUS_USERNAME=admin \
  YUANTUS_PASSWORD=admin \
  bash scripts/verify_ops_health.sh http://127.0.0.1:7910 tenant-1 org-1
```

如需检查外部依赖，可设置：

```bash
export YUANTUS_HEALTHCHECK_EXTERNAL=true
```

### 37.2 验证内容

- `/api/v1/health/deps` 返回 `ok=true`
- `deps.db/identity_db/storage` 均为 `ok=true`

---

## 38) CAD Missing Source 验收脚本

### 38.1 一键验收：`scripts/verify_cad_missing_source.sh`

该脚本验证源文件缺失时，CAD 任务不会进入重试风暴（一次失败即标记为 FAILED）。

```bash
export YUANTUS_STORAGE_TYPE=local
export YUANTUS_LOCAL_STORAGE_PATH=./data/storage

DB_URL='sqlite:///./tmp_missing_source.db' \
  IDENTITY_DB_URL='sqlite:///./tmp_missing_source_identity.db' \
  bash scripts/verify_cad_missing_source.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 38.2 验证内容

- 删除源文件后执行 preview job
- Job 状态为 `failed` 且 `attempt_count=1`
- `last_error` 含 `Source file missing`

---

## 39) Baseline（BOM Snapshot）验收脚本

### 39.1 一键验收：`scripts/verify_baseline.sh`

该脚本验证 Baseline 创建、对比、以及 Baseline-to-Baseline Diff。

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_baseline.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 39.2 验证内容

- 创建 BOM 树（A→B/C）并生成 Baseline
- Baseline vs 当前 BOM：无差异
- 修改 BOM（改数量 + 新增子件）后差异正确
- Baseline-to-Baseline diff 可用

### 39.3 API 端点

- `POST /api/v1/baselines` 创建 Baseline（支持 `root_item_id` 或 `root_version_id`）
- `GET /api/v1/baselines` 列表（支持筛选）
- `GET /api/v1/baselines/{id}` 获取 Baseline
- `POST /api/v1/baselines/{id}/compare` 与 item/version/baseline 对比

---

## 40) Backup/Restore（私有化备份与恢复）

### 40.1 一键验收：`scripts/verify_backup_restore.sh`

该脚本会执行：

- Postgres 备份（`pg_dump`）并生成 `.dump`
- MinIO bucket 备份（`mc mirror`）
- 使用隔离的 DB/bucket 进行恢复验证（避免覆盖线上）

```bash
bash scripts/verify_backup_restore.sh
```

### 40.2 说明

- 备份脚本：`scripts/backup_private.sh`
- 恢复脚本：`scripts/restore_private.sh`
- 恢复默认需设置 `CONFIRM=yes`

---

## 41) Cleanup（清理恢复产物）

### 41.1 一键验收：`scripts/verify_cleanup_restore.sh`

该脚本创建临时 DB + bucket，并验证 cleanup 脚本可移除它们。

```bash
bash scripts/verify_cleanup_restore.sh
```

### 41.2 说明

- 清理脚本：`scripts/cleanup_private_restore.sh`
- 需要设置 `CONFIRM=yes`

---

## 42) Scheduled Backup（定时备份与轮转）

### 42.1 一键验收：`scripts/verify_backup_rotation.sh`

该脚本创建临时备份目录并验证轮转只保留最新 N 份。

```bash
bash scripts/verify_backup_rotation.sh
```

### 42.2 说明

- 定时备份脚本：`scripts/backup_scheduled.sh`
- 轮转脚本：`scripts/backup_rotate.sh`

---

## 43) Quota（租户配额）

### 43.1 一键验收：`scripts/verify_quotas.sh`

该脚本验证用户/组织/文件/任务配额的 enforce 行为。

```bash
export YUANTUS_QUOTA_MODE=enforce
bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 43.2 验证内容

- `/api/v1/admin/quota` 返回 `mode=enforce`
- `PUT /api/v1/admin/quota` 可设置限制
- 新建用户/组织在超限时返回 `HTTP 429`
- 文件上传超限时返回 `HTTP 429`
- Job 创建超限时返回 `HTTP 429`

---

## 44) Equivalents（等效件）

### 44.1 一键验收：`scripts/verify_equivalents.sh`

该脚本验证 Part 等效件的增删改查（包含去重与自引用校验）。

```bash
bash scripts/verify_equivalents.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 44.2 手动验证（示例）

```bash
# 1) Add equivalent
curl -X POST 'http://127.0.0.1:7910/api/v1/items/{item_id}/equivalents' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"equivalent_item_id":"{other_id}","properties":{"rank":1}}'

# 2) List equivalents
curl 'http://127.0.0.1:7910/api/v1/items/{item_id}/equivalents' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN"

# 3) Remove equivalent
curl -X DELETE 'http://127.0.0.1:7910/api/v1/items/{item_id}/equivalents/{equivalent_id}' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN"
```

---

## 45) MBOM Convert（EBOM → MBOM）

### 45.1 一键验收：`scripts/verify_mbom_convert.sh`

该脚本验证 EBOM 转换为 MBOM，并校验关系/替代件复制。

```bash
bash scripts/verify_mbom_convert.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 45.2 手动验证（示例）

```bash
curl -X POST 'http://127.0.0.1:7910/api/v1/bom/convert/ebom-to-mbom' \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"root_id":"{ebom_root_id}"}'

# 查询 MBOM 树
curl 'http://127.0.0.1:7910/api/v1/bom/mbom/{mbom_root_id}/tree?depth=2' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer $TOKEN"
```

---

## 46) S2 Documents & Files（文件/文档产品化）

### 46.1 一键验收：`scripts/verify_documents.sh`

该脚本验证文件元数据（作者/来源/版本）、去重策略以及 Item 挂载列表可回读。

```bash
bash scripts/verify_documents.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 46.2 额外说明（可选）

- 上传限制可通过环境变量控制：
  - `YUANTUS_FILE_UPLOAD_MAX_BYTES`：最大上传字节数（0 表示不限制）
  - `YUANTUS_FILE_ALLOWED_EXTENSIONS`：允许扩展名白名单（逗号分隔、无点）

---

## 47) Document Lifecycle（Controlled Release）

### 47.1 一键验收：`scripts/verify_document_lifecycle.sh`

该脚本验证 Document 的生命周期流转与 Released 状态的强制锁定：

- Draft → Review → Released
- Released 后 AML update 返回 409
- Released 后文件 attach 返回 409

```bash
bash scripts/verify_document_lifecycle.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 48) Part Lifecycle（Released 锁定 BOM）

### 48.1 一键验收：`scripts/verify_part_lifecycle.sh`

该脚本验证 Part 的生命周期流转与 Released 状态的 BOM/更新/附件锁定：

- Draft → Review → Released
- Released 后 AML update 返回 409
- Released 后 BOM add/remove 返回 409
- Released 后文件 attach 返回 409

```bash
bash scripts/verify_part_lifecycle.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 49) CAD Connectors Config（自定义连接器配置）

### 49.1 一键验收：`scripts/verify_cad_connectors_config.sh`

该脚本验证自定义连接器配置可被 reload 并参与 `/cad/import` 解析。

```bash
bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

说明：脚本通过 `POST /api/v1/cad/connectors/reload` 发送内联 JSON 配置。

---

## 50) CAD Sync Template（属性映射模板）

### 50.1 一键验收：`scripts/verify_cad_sync_template.sh`

该脚本验证 CAD 属性模板的导出/导入流程：

- `GET /cad/sync-template/{item_type}` 下载 CSV
- `POST /cad/sync-template/{item_type}` 应用 CSV

```bash
bash scripts/verify_cad_sync_template.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 50.2) CAD OCR Title Block（图纸 OCR 字段）

### 50.2.1 一键验收：`scripts/verify_cad_ocr_titleblock.sh`

该脚本调用 CAD ML Vision OCR，验证 `cad_ml_vision` 会将标题栏字段合并到 `cad_attributes`：

- `drawing_no`
- `material`
- `part_name`
- `revision`（可选）
- `weight`（可选）

运行前确保 CAD ML Vision 服务可用：

```bash
export YUANTUS_CAD_ML_BASE_URL='http://localhost:8001'
```

可选参数：

- `CAD_OCR_SAMPLE_FILE`：指定样例图片（PNG/JPG）。
- `CAD_OCR_ALLOW_EMPTY=1`：允许 OCR 空结果（仅校验流程）。

```bash
bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 50.3) CAD 2D Preview（DWG/DXF 渲染）

### 50.3.1 一键验收：`scripts/verify_cad_preview_2d.sh`

该脚本调用 CAD ML Render 服务，将 DWG/DXF 渲染为 PNG，并验证 `/file/{id}/preview` 可访问：

- DWG/DXF 上传
- 触发 `cad_preview` 生成 PNG 预览
- 预览端点返回 200/302

运行前确保 CAD ML Render 服务可用：

```bash
export YUANTUS_CAD_ML_BASE_URL='http://localhost:8001'
```

可选参数：

- `CAD_PREVIEW_SAMPLE_FILE`：指定 DWG/DXF 样例文件。

```bash
bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 50.4) CAD Filename Parsing（文件名解析）

### 50.4.1 一键验收：`scripts/verify_cad_filename_parse.sh`

验证文件名解析的兜底逻辑，可补足 CAD 提取缺失字段：

- `part_number`
- `drawing_no`
- `part_name`
- `revision`

覆盖样例：

- `model2.prt.1` → revision=`1`
- `J2824002-06上封头组件v2.dwg` → part_number=`J2824002-06`, part_name=`上封头组件`
- `比较_J2825002-09下轴承支架组件v2.dwg` → 过滤前缀、保留版本

```bash
bash scripts/verify_cad_filename_parse.sh
```

---

## 50.5) CAD Extract Local（Key-Value 解析）

### 50.5.1 一键验收：`scripts/verify_cad_extract_local.sh`

验证本地 Key-Value 提取能力（支持重量带单位解析）：

- `part_number`/`drawing_no`
- `description`
- `revision`
- `material`
- `weight`（如 `1.2kg` → `1.2`）

```bash
bash scripts/verify_cad_extract_local.sh
```

---

## 50.6) CAD Attribute Normalization（材料/重量/版本）

### 50.6.1 一键验收：`scripts/verify_cad_attribute_normalization.sh`

验证 CAD 属性归一化：

- `material`：中英文材料映射（如不锈钢304 → Stainless Steel 304）
- `weight`：支持单位换算（g/kg/吨 → kg）
- `revision`：去除 `REV/VER/VERSION` 前缀
- `drawing_no`：缺失时由 `part_number` 补齐
- 关键别名：`图纸编号`/`图纸名称`/`版次`/`材质`/`重量(kg)`

```bash
bash scripts/verify_cad_attribute_normalization.sh
```

---

## 51) CAD Extractor External（真实提取对接）

### 51.1 一键验收：`scripts/verify_cad_extractor_stub.sh`

该脚本启动本地 extractor stub 服务，验证 `cad_extract` 走外部服务并返回 `source=external`。

```bash
bash scripts/verify_cad_extractor_stub.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 51.2 真实服务验收：`scripts/verify_cad_extractor_external.sh`

需要提供真实 CAD 文件与外部服务地址：

```bash
docker compose -f docker-compose.cad-extractor.yml up -d

export CAD_EXTRACTOR_BASE_URL='http://host.docker.internal:8200'
export CAD_EXTRACTOR_SAMPLE_FILE='/path/to/sample.dwg'
export CAD_EXTRACTOR_SERVICE_TOKEN='...'
export CAD_EXTRACTOR_EXPECT_KEY='part_number'
# 可选: CAD_EXTRACTOR_EXPECT_VALUE='ABC-001'

RUN_CAD_EXTRACTOR_EXTERNAL=1 \
  bash scripts/verify_cad_extractor_external.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 51.3 微服务自检：`scripts/verify_cad_extractor_service.sh`

仅验证 extractor 微服务本身，不依赖 Yuantus API：

```bash
docker compose up -d cad-extractor

RUN_CAD_EXTRACTOR_SERVICE=1 \
  bash scripts/verify_cad_extractor_service.sh http://127.0.0.1:8200
```

---

## 51.4) CAD Real Samples（DWG/STEP/PRT 实测）

### 51.4.1 一键验收：`scripts/verify_cad_real_samples.sh`

验证真实 CAD 文件链路：导入 → cad_extract → cad_preview → auto_create_part。

默认样本（可通过环境变量覆盖）：

- `CAD_SAMPLE_DWG`：`/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg`
- `CAD_SAMPLE_STEP`：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp`
- `CAD_SAMPLE_PRT`：`/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt`

执行命令：

```bash
export CAD_EXTRACTOR_BASE_URL='http://localhost:8200'
export CAD_ML_BASE_URL='http://localhost:8001'

bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1
```

验收要点：

- `item_number` 取文件名前缀（如 `J2824002-06`/`CNC`/`model2`）
- `revision` 在文件名末尾包含 `vN` 时校验（如 `v2`）
- `preview` 端点可返回 `200/302`

---

## 51.5) CAD 2D Connector Coverage（Offline）

使用 `scripts/collect_cad_extractor_coverage.py` 的 `--offline` 模式，
直接走本地连接器（SQLite + 本地存储），无需 API / Extractor 服务。

也可通过回归封装脚本执行：

```bash
export CAD_CONNECTOR_COVERAGE_DIR=/path/to/dwg
RUN_CAD_CONNECTOR_COVERAGE_2D=1 \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

示例（训练图纸 DWG）：

```bash
.venv/bin/python scripts/collect_cad_extractor_coverage.py \
  --offline \
  --cad-format HAOCHEN \
  --cad-connector-id haochencad \
  --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
  --extensions dwg \
  --report-title "CAD 2D Connector Coverage Report (Haochen, Offline)" \
  --output docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md

.venv/bin/python scripts/collect_cad_extractor_coverage.py \
  --offline \
  --cad-format ZHONGWANG \
  --cad-connector-id zhongwangcad \
  --dir /Users/huazhou/Downloads/训练图纸/训练图纸 \
  --extensions dwg \
  --report-title "CAD 2D Connector Coverage Report (Zhongwang, Offline)" \
  --output docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md
```

可选参数：

- `--max-files N`：按数量抽样
- `--force-unique`：对上传文件追加标记，绕过去重

---

## 52) Search Reindex（索引状态 + 重建）

### 52.1 一键验收：`scripts/verify_search_reindex.sh`

该脚本验证 Search 状态与重建接口：

- `GET /api/v1/search/status` 返回 engine/index
- `POST /api/v1/search/reindex` 返回 indexed 数量
- `GET /api/v1/search/?q=...` 搜索结果可命中

```bash
bash scripts/verify_search_reindex.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 53) Tenant Provisioning（平台管理员创建租户）

### 53.1 一键验收：`scripts/verify_tenant_provisioning.sh`

该脚本验证平台管理员能力：

- `GET /api/v1/admin/tenants` 可用
- `POST /api/v1/admin/tenants` 创建 tenant + 默认 org + admin
- `POST /api/v1/admin/tenants/{tenant_id}/orgs` 创建额外 org
- 新租户 admin 可登录并访问 `/api/v1/admin/tenant`

运行前确保平台管理员开关启用：

```bash
export YUANTUS_PLATFORM_ADMIN_ENABLED=true
```

```bash
bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 54) Product Detail Mapping（属性/版本/附件聚合）

### 54.1 一键验收：`scripts/verify_product_detail.sh`

该脚本验证产品详情聚合接口：

- `GET /api/v1/products/{item_id}` 返回 `item/current_version/versions/files`
- 校验 `item_number` 映射、版本初始化、附件列表

```bash
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 55) BOM UI 关键接口（where-used / compare / substitutes）

### 55.1 一键验收：`scripts/verify_bom_ui.sh`

该脚本验证 UI 侧依赖的 BOM API：

- `GET /api/v1/bom/{item_id}/where-used`
- `GET /api/v1/bom/compare`（`include_child_fields=true`）
- `POST/GET /api/v1/bom/{bom_line_id}/substitutes`

```bash
bash scripts/verify_bom_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 56) Docs + Approval（文档流程 + ECO 审批）

### 56.1 一键验收：`scripts/verify_docs_approval.sh`

该脚本串联以下验证：

- `verify_documents.sh`（文档/附件）
- `verify_document_lifecycle.sh`（文档生命周期）
- ECO 审批流程（stage → approve → approvals）

```bash
bash scripts/verify_docs_approval.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 57) CAD Connectors（GStarCAD/ZWCAD/Haochen/Zhongwang）

### 57.1 一键验收：`scripts/verify_cad_connectors.sh`

默认验证 2D 连接器（合成文件），可选开启真实样本：

```bash
bash scripts/verify_cad_connectors.sh http://127.0.0.1:7910 tenant-1 org-1
```

启用真实样本：

```bash
RUN_REAL=1 \
  bash scripts/verify_cad_connectors.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 58) Ops Hardening（多租户/配额/审计/健康/索引）

### 58.1 一键验收：`scripts/verify_ops_hardening.sh`

```bash
bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 58.2 配额/审计强制模式示例

启用配额与审计后再执行验收脚本：

```bash
export YUANTUS_QUOTA_MODE=enforce
export YUANTUS_AUDIT_ENABLED=true

docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build
bash scripts/verify_ops_hardening.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2
```

### 58.3 多租户迁移（migrations 模式）

当 `SCHEMA_MODE=migrations` 时，请先执行多租户迁移：

```bash
export YUANTUS_TENANCY_MODE=db-per-tenant-org
export YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg

./scripts/mt_migrate.sh
```

---

## 59) BOM Compare Field Contract（字段级对照）

### 59.1 一键验收：`scripts/verify_bom_compare_fields.sh`

该脚本验证 BOM compare 返回字段级对照与标准化字段：

- `before_line/after_line` 含 `quantity/uom/find_num/refdes/effectivity/substitutes`
- `before_normalized/after_normalized` 含对应标准化字段
- `changes` 至少包含 `quantity/find_num` 变更
- `/api/v1/bom/compare/schema` 返回字段清单与 compare_mode

```bash
bash scripts/verify_bom_compare_fields.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 59.2 BOM Compare Schema Endpoint

新增 `/api/v1/bom/compare/schema` 用于前端获取字段级对照与 compare_mode：

```bash
curl -s http://127.0.0.1:7910/api/v1/bom/compare/schema \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -H "Authorization: Bearer <token>"
```

期望包含：

- `line_fields`：字段 + severity + normalization
- `compare_modes`：`only_product/summarized/num_qty/by_position/by_reference`
- `line_key_options`：所有 line_key 策略

字段级对照详见：`docs/BOM_COMPARE_FIELD_MAPPING.md`。

---

## 60) Product UI Aggregation（产品详情聚合）

### 60.1 一键验收：`scripts/verify_product_ui.sh`

该脚本验证 `/products/{id}` 的 UI 聚合输出：

- `bom_summary`（直接子件、总子件、深度）
- `where_used_summary`（被引用统计与样本）

```bash
bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

如果本机无法访问 `localhost`（受限沙箱/网络策略），可用本地 TestClient 方式：

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_product_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 61) Where-Used UI Payload（Where-Used UI 输出）

### 61.1 一键验收：`scripts/verify_where_used_ui.sh`

该脚本验证 where-used 输出包含 line 字段与递归标记：

- `line/line_normalized` 字段存在
- `recursive/max_levels` 回显

```bash
bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

如本机网络受限，可用：

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_where_used_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 62) Docs + ECO UI Summary（文档/审批聚合）

### 62.1 一键验收：`scripts/verify_docs_eco_ui.sh`

该脚本验证产品详情输出中：

- `document_summary` 生命周期统计
- `eco_summary` 审批与变更统计

```bash
bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

如本机网络受限，可用：

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_docs_eco_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 63) S8 Ops Monitoring（配额/审计/报表元信息）

### 63.1 一键验收：`scripts/verify_ops_s8.sh`

该脚本串行验证：

- `verify_quotas.sh`（含 `/admin/tenants/quotas` 监控输出）
- `verify_audit_logs.sh`（含 `/admin/audit/retention` 与 `/admin/audit/prune`）
- `verify_reports_summary.sh`（`meta` 字段）

```bash
# 必需开关
export YUANTUS_QUOTA_MODE=enforce
export YUANTUS_AUDIT_ENABLED=true
export YUANTUS_PLATFORM_ADMIN_ENABLED=true

# 可选：审计留存配置（便于 retention 验证）
export YUANTUS_AUDIT_RETENTION_DAYS=1
export YUANTUS_AUDIT_RETENTION_MAX_ROWS=10
export YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1

bash scripts/verify_ops_s8.sh http://127.0.0.1:7910 tenant-1 org-1
```

> 若需验证 retention days 强制清理，需设置 `IDENTITY_DB_URL`/`YUANTUS_IDENTITY_DATABASE_URL` 以便脚本回写审计记录时间。

---

## 64) Deprecated Relationship Write Monitor

`meta_relationships` 已降级为只读兼容层，写入会被拦截并记录进程内统计。

```bash
export YUANTUS_PLATFORM_ADMIN_ENABLED=true

curl -s "http://127.0.0.1:7910/api/v1/admin/relationship-writes?window_seconds=86400&recent_limit=20&warn_threshold=10" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1" \
  -H "Authorization: Bearer $PLATFORM_ADMIN_TOKEN"
```

> 说明：该统计为进程内计数，重启服务后会清零。`warn_threshold=0` 表示关闭告警。

（可选）仅开发环境可用的模拟触发：

```bash
export YUANTUS_RELATIONSHIP_SIMULATE_ENABLED=true

curl -s -X POST "http://127.0.0.1:7910/api/v1/admin/relationship-writes/simulate?operation=insert&warn_threshold=10" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1" \
  -H "Authorization: Bearer $PLATFORM_ADMIN_TOKEN"
```

---

## 65) Relationship → Item Migration (Phase 2)

脚本：`scripts/migrate_relationship_items.py`

```bash
python scripts/migrate_relationship_items.py --dry-run
```

多租户模式：

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
python scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --dry-run
```

完整说明见 `docs/MIGRATION_RELATIONSHIP_ITEMS.md`。

---

## 66) Where-Used Line Schema

验证 where-used 行字段 schema 输出：

```bash
bash scripts/verify_where_used_schema.sh http://127.0.0.1:7910 tenant-1 org-1
```

---

## 67) Local Regression (TestClient)

无需绑定端口或启动 Docker 的本地回归集合：

```bash
LOCAL_TESTCLIENT=1 bash scripts/verify_all_local.sh http://127.0.0.1:7910 tenant-1 org-1
```
