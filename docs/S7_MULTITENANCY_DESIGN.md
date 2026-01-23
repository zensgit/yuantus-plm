# S7 多租户深度验证设计说明

目标：在 `db-per-tenant-org` 模式下验证隔离、配额、审计、健康与索引回归能力，确保私有化交付具备最小 SaaS 运营能力。

## 1. 验证范围

- **多租户隔离**：tenant/org 维度数据不串库、不串数据。
- **配额（Quota）**：用户数、组织数、文件数、存储、任务并发等限制在 `enforce` 模式下可阻断。
- **审计（Audit）**：访问记录能写入审计日志，并可通过 `/admin/audit` 查询与留存校验。
- **健康检查**：`/health`、`/health/deps` 正常，并包含 identity/storage 状态。
- **索引回归**：`/search/reindex` 可重建索引并可检索新增条目。

## 2. 环境与依赖

- Docker Compose 组合：
  - `docker-compose.yml`
  - `docker-compose.mt.yml`
- 关键环境变量：
  - `YUANTUS_TENANCY_MODE=db-per-tenant-org`
  - `YUANTUS_SCHEMA_MODE=create_all`
  - `YUANTUS_QUOTA_MODE=enforce`
  - `YUANTUS_AUDIT_ENABLED=true`
  - `YUANTUS_PLATFORM_ADMIN_ENABLED=true`
  - `YUANTUS_AUDIT_RETENTION_DAYS=1`（可选）
  - `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`（可选）
  - `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`（可选）

## 3. 设计要点

### 3.1 多租户隔离（db-per-tenant-org）

- 数据库 URL 使用模板：
  - `yuantus_mt_pg__{tenant_id}__{org_id}`
- 服务层通过 `tenant_id/org_id` 上下文解析 DB URL：
  - `resolve_database_url()` -> `get_db()`
- 验证策略：
  - tenant A/org A 写入的 Part 不被 tenant A/org B、tenant B/org A 读取。

### 3.2 配额 Enforcement

- 开启 `YUANTUS_QUOTA_MODE=enforce` 后：
  - `/admin/quota` 可更新租户配额阈值。
  - 创建 Org/User/File/Job 超额返回 429。
- 验证策略：
  - 将配额设置为 “当前使用 + 1”。
  - 第 2 次新增操作必须被拒绝。

### 3.3 审计日志

- 开启 `YUANTUS_AUDIT_ENABLED=true`。
- `/admin/audit` 查询 `/api/v1/health` 的访问记录。
- 验证策略：
  - 先触发一次 health 请求；
  - 再查询 audit 并确认有对应记录。
  - 若开启 retention：验证 old log 清理与 retention endpoints。

### 3.4 健康检查与索引回归

- `/health`、`/health/deps` 应返回 ok=true 且 db/identity/storage 状态可用。
- `/search/reindex` 可重建索引并检索新增 item_number。

## 4. 退出条件（DoD）

- `verify_ops_hardening.sh` 通过（包含 multi-tenancy、quota、audit、health、reindex）。
- 如启用 retention/平台管理员：对应校验通过。

## 5. 输出物

- `docs/S7_MULTITENANCY_VERIFICATION.md`：完整验证记录与命令。
- `docs/VERIFICATION_RESULTS.md`：追加 S7 深度验证结果。

## 6. 执行入口

- 统一入口脚本：`scripts/verify_s7.sh`
- 该脚本依次执行：
  - `verify_ops_hardening.sh`（multi-tenancy + quota + audit + health + reindex）
  - `verify_tenant_provisioning.sh`（平台管理员租户/组织创建）
