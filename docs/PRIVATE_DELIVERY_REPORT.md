# YuantusPLM 私有化交付底座实施报告

> 执行时间：2025-12-18
> 目标：实现 S0/S2 私有化交付能力，使系统可在 PostgreSQL + MinIO 环境下稳定部署

---

## 1. 实施概览

### 1.1 核心改动点（按用户反馈的"必须改"）

| 改动点 | 状态 | 说明 |
|--------|------|------|
| ✅ **SCHEMA_MODE 开关** | 已完成 | 新增 `YUANTUS_SCHEMA_MODE=create_all|migrations` 配置 |
| ✅ **Dockerfile 构建顺序** | 已完成 | 先 `COPY src/` 再 `pip install .`（非 editable） |
| ✅ **MinIO presigned URL 可达性** | 已完成 | 内部用 `minio:9000`，对外 presigned URL 用 `localhost:59000` |

### 1.2 功能实现清单

| 功能 | 状态 | 说明 |
|------|------|------|
| PostgreSQL 支持 | ✅ | `psycopg[binary]` 驱动，完整迁移支持 |
| Alembic 迁移 | ✅ | `yuantus db upgrade/revision/downgrade` |
| S3/MinIO 存储 | ✅ | `boto3` 驱动，bucket 自动创建 |
| Job 并发安全 | ✅ | PostgreSQL `FOR UPDATE SKIP LOCKED` |
| Docker 化交付 | ✅ | `Dockerfile` + `Dockerfile.worker` |
| 一键启动 | ✅ | `docker compose up --build` |

---

## 2. 技术实现详情

### 2.1 SCHEMA_MODE 配置

**位置**：`src/yuantus/config/settings.py`

```python
SCHEMA_MODE: str = Field(
    default="create_all",
    description="create_all: auto-create tables (dev), migrations: use Alembic only (prod)",
)
```

**行为**：
- `create_all`（默认）：自动建表，适用于开发环境
- `migrations`：禁止自动建表，空库时 `seed-*` 报错提示先跑 `yuantus db upgrade`

**验证**：
```bash
# 空库下 SCHEMA_MODE=migrations 会报错
YUANTUS_SCHEMA_MODE=migrations yuantus seed-meta
# RuntimeError: SCHEMA_MODE=migrations: Database is empty. Run `yuantus db upgrade` first...
```

### 2.2 Alembic 迁移系统

**新增文件**：
- `alembic.ini` - Alembic 配置
- `migrations/env.py` - 迁移环境（自动加载所有 models）
- `migrations/script.py.mako` - 迁移模板
- `migrations/versions/f87ce5711ce1_initial_schema.py` - 初始 schema（55KB，~80 张表）

**CLI 命令**：
```bash
yuantus db upgrade          # 执行迁移到 head
yuantus db downgrade -r -1  # 回退一个版本
yuantus db revision -m "msg" # 生成新迁移
yuantus db current          # 查看当前版本
yuantus db history          # 查看迁移历史
```

### 2.3 Job 并发安全

**位置**：`src/yuantus/meta_engine/services/job_service.py`

```python
def poll_next_job(self, worker_id: str) -> Optional[ConversionJob]:
    dialect = self.session.bind.dialect.name if self.session.bind else "unknown"

    query = (
        self.session.query(ConversionJob)
        .filter(...)
        .order_by(asc(ConversionJob.priority), asc(ConversionJob.created_at))
    )

    # PostgreSQL: Use SKIP LOCKED to prevent race conditions
    if dialect == "postgresql":
        query = query.with_for_update(skip_locked=True)

    job = query.first()
    # ...
```

**效果**：多个 worker 并行处理时，每个 job 只被一个 worker 领取。

### 2.4 S3/MinIO 存储初始化

**CLI 命令**：
```bash
yuantus init-storage  # 创建 S3 bucket（如不存在）
```

**presigned URL 处理**：
- 文件下载端点 (`/api/v1/file/{id}/download`) 已支持 302 重定向到 presigned URL
- docker-compose 中：
  - `YUANTUS_S3_ENDPOINT_URL=http://minio:9000`（容器内读写）
  - `YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000`（返回给宿主机客户端的 URL）

---

## 3. 依赖变更

**pyproject.toml 新增**：
```toml
dependencies = [
  ...
  # Private deployment dependencies
  "psycopg[binary]>=3.1.0",  # PostgreSQL 驱动
  "alembic>=1.13.0",          # 数据库迁移
  "boto3>=1.34.0",            # S3/MinIO 客户端
]
```

---

## 4. Docker 交付

### 4.1 Dockerfile（API 服务）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY plugins/ ./plugins/
COPY alembic.ini ./
COPY migrations/ ./migrations/
RUN pip install --no-cache-dir .
EXPOSE 7910
CMD ["yuantus", "start"]
```

### 4.2 Dockerfile.worker（Worker 服务）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY plugins/ ./plugins/
RUN pip install --no-cache-dir .
CMD ["yuantus", "worker", "--poll-interval", "5"]
```

### 4.3 docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports:
      - "55432:5432"  # 避免端口冲突

  minio:
    image: minio/minio:latest
    ports:
      - "59000:9000"
      - "59001:9001"

  api:
    build: .
    ports:
      - "7910:7910"
    environment:
      YUANTUS_DATABASE_URL: postgresql+psycopg://yuantus:yuantus@postgres:5432/yuantus
      YUANTUS_SCHEMA_MODE: migrations
      YUANTUS_STORAGE_TYPE: s3
      YUANTUS_S3_ENDPOINT_URL: http://minio:9000
      YUANTUS_S3_PUBLIC_ENDPOINT_URL: http://localhost:59000
    command: >
      sh -c "yuantus db upgrade && yuantus init-storage && yuantus start"

  worker:
    build:
      dockerfile: Dockerfile.worker
    environment:
      YUANTUS_DATABASE_URL: postgresql+psycopg://yuantus:yuantus@postgres:5432/yuantus
      YUANTUS_S3_ENDPOINT_URL: http://minio:9000
      YUANTUS_S3_PUBLIC_ENDPOINT_URL: http://localhost:59000
```

---

## 5. 验收结果

### 5.1 Run H 全链路验证（PostgreSQL + MinIO）

**执行命令**：
```bash
docker compose up -d postgres minio
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'
export YUANTUS_SCHEMA_MODE=migrations

yuantus db upgrade
yuantus init-storage
yuantus start --port 7910 &

bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

**结果**：
```
==> Seed identity/meta
==> Login
==> Health
Health: OK
==> Meta metadata (Part)
Meta metadata: OK
==> AML add/get
AML add: OK (part_id=7fafaff1-be59-4fd8-96c9-bb24e1f0f55b)
AML get: OK
==> Search
Search: OK
==> RPC Item.create
RPC Item.create: OK (part_id=9e4386c7-6691-4619-90f4-9a5573aee163)
==> File upload/download
File upload: OK (file_id=45b046de-3705-42e9-b13e-4c0fcfe676d9)
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
==> Integrations health
Integrations health: OK (ok=False)

ALL CHECKS PASSED
```

### 5.2 SCHEMA_MODE=migrations 阻止机制验证

**测试**：空库下运行 `seed-meta`
```bash
YUANTUS_DATABASE_URL='sqlite:///empty.db' YUANTUS_SCHEMA_MODE=migrations yuantus seed-meta
```

**结果**：
```
RuntimeError: SCHEMA_MODE=migrations: Database is empty.
Run `yuantus db upgrade` first to create tables via Alembic.
```

✅ 符合预期，阻止了 `create_all()` 掩盖 Alembic 问题。

### 5.3 Job 并发安全验证（2 worker / 10 jobs）

**方式**：docker compose 场景下把 `worker` 扩到 2 个实例，创建 10 个 `cad_conversion` job。

**验收点**：
- 10 个 job 最终全部 `completed`
- 每个 job 的 `attempt_count == 1`（无重复领取/处理）

✅ 验证通过。

---

## 6. 部署指南

### 6.1 本机开发（docker 仅提供基础设施）

```bash
# 启动 Postgres/MinIO
docker compose up -d postgres minio

# 设置环境变量
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'

# 运行迁移
yuantus db upgrade

# 初始化存储
yuantus init-storage

# 启动服务
YUANTUS_AUTH_MODE=required yuantus start --port 7910

# 验证
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 6.2 Docker 一键部署

```bash
# 构建并启动
docker compose up --build

# 等待服务就绪
curl http://localhost:7910/api/v1/health

# 验证
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 6.3 运维 Runbook（备份/恢复/轮转/清理/审计/配额）

- 备份/恢复/清理：`docs/RUNBOOK_BACKUP_RESTORE.md`
  - 相关脚本：`scripts/backup_private.sh` / `scripts/restore_private.sh` / `scripts/cleanup_private_restore.sh`
  - 验证：`scripts/verify_backup_restore.sh` / `scripts/verify_cleanup_restore.sh`
- 定时备份与轮转：`docs/RUNBOOK_SCHEDULED_BACKUP.md`
  - 相关脚本：`scripts/backup_scheduled.sh` / `scripts/backup_rotate.sh`
  - 验证：`scripts/verify_backup_rotation.sh`
- 运行/回滚（多租户 + 审计）：`docs/RUNBOOK_RUNTIME.md`
  - 启用/回退 `db-per-tenant-org` 与 `audit_enabled`
- 审计与配额（环境开关）：
  - 审计：`YUANTUS_AUDIT_ENABLED=true` + `scripts/verify_audit_logs.sh`
  - 配额：`YUANTUS_QUOTA_MODE=enforce` + `scripts/verify_quotas.sh`

验证结果已记录在 `docs/VERIFICATION_RESULTS.md`（BK-4/BK-5/BK-6, AUDIT-RET-2, S7-Q-3）。

---

## 7. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `pyproject.toml` | 修改 | 添加 psycopg, alembic, boto3 |
| `src/yuantus/config/settings.py` | 修改 | 添加 SCHEMA_MODE 配置 |
| `src/yuantus/database.py` | 修改 | 支持 SCHEMA_MODE 阻止逻辑 |
| `src/yuantus/cli.py` | 修改 | 添加 db, init-storage 命令 |
| `src/yuantus/meta_engine/services/job_service.py` | 修改 | PostgreSQL skip_locked |
| `alembic.ini` | 新建 | Alembic 配置 |
| `migrations/env.py` | 新建 | 迁移环境 |
| `migrations/script.py.mako` | 新建 | 迁移模板 |
| `migrations/versions/f87ce5711ce1_initial_schema.py` | 新建 | 初始 schema |
| `Dockerfile` | 新建 | API 镜像 |
| `Dockerfile.worker` | 新建 | Worker 镜像 |
| `docker-compose.yml` | 修改 | 添加 api, worker 服务 |
| `README.md` | 已存在 | 无需修改 |

---

## 8. 后续建议

1. **生产部署**：
   - 修改 `YUANTUS_JWT_SECRET_KEY` 为强密钥
   - 配置 `YUANTUS_S3_PUBLIC_ENDPOINT_URL` 为客户端可访问的 MinIO 域名
   - 添加 HTTPS 反向代理

2. **监控**：
   - 添加 Prometheus metrics 端点
   - 配置 worker 健康检查

3. **扩展**：
   - 支持多 worker 实例水平扩展
   - 添加 Redis 作为缓存层

---

**报告生成时间**：2025-12-18 23:15 CST
