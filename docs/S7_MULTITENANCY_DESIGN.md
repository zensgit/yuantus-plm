# S7 多租户深度验证设计说明

目标：在 `db-per-tenant-org` 模式下验证隔离、配额与审计三项能力，确保私有化交付具备最小 SaaS 运营能力。

## 1. 验证范围

- **多租户隔离**：tenant/org 维度数据不串库、不串数据。
- **配额（Quota）**：用户数、组织数、文件数、存储、任务并发等限制在 `enforce` 模式下可阻断。
- **审计（Audit）**：访问记录能写入审计日志，并可通过 `/admin/audit` 查询。

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

## 4. 退出条件（DoD）

- `verify_multitenancy.sh` 通过。
- `verify_quotas.sh` 通过（enforce）。
- `verify_audit_logs.sh` 通过（audit_enabled=true）。

## 5. 输出物

- `docs/S7_MULTITENANCY_VERIFICATION.md`：完整验证记录与命令。
- `docs/VERIFICATION_RESULTS.md`：追加 S7 深度验证结果。
