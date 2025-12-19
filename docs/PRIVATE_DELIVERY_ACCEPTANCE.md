# 私有化交付底座（Postgres + MinIO）验收说明（S0/S2）

目标：让 `yuantus-plm` 在 **PostgreSQL + MinIO(S3)** 环境下可稳定私有化部署，并且验收是“真实有效”的（不会被 `create_all()` 掩盖）。

> 执行全链路功能验证脚本：`scripts/verify_run_h.sh`（等同于 `docs/VERIFICATION.md` 的 Run H）。

---

## 1) 对 Claude 计划的关键修改点（必须做）

### 1.1 禁止 `create_all()` 掩盖 Alembic（否则验收失真）

现状：

- `yuantus seed-meta`/`seed-identity` 会 `create_all()` 建表。
- `get_db()` 在 `ENVIRONMENT=dev` 下也会自动 `create_all()`（db-per-tenant 模式尤甚）。

结果：即便 Alembic 不完整，Run H 也可能“看起来通过”。

**必须引入一个“schema 模式开关”**（命名可选，但要全局一致）：

- 例如 `YUANTUS_SCHEMA_MODE=create_all|migrations`（建议默认 `create_all`，生产用 `migrations`）

在 `migrations` 模式下：

- 禁止任何自动建表（包括 `seed-*`、`get_db()` 自动 init）
- 如果表不存在，`seed-*` 需要报清晰错误：提示先跑 `yuantus db upgrade`

### 1.2 Dockerfile 构建顺序修正（否则 build 必挂）

你计划里的 Dockerfile：

```dockerfile
COPY pyproject.toml .
RUN pip install -e .
COPY src/ src/
```

问题：`pip install -e .` 时 `src/` 还没复制进镜像，安装会失败。

**修正建议：**

- 先 `COPY pyproject.toml README.md ./` + `COPY src/ ./src` 再安装
- 生产镜像优先 `pip install .`（而不是 editable）

### 1.3 MinIO presigned URL 的“可达性”必须明确

如果 API 运行在 docker 内，`YUANTUS_S3_ENDPOINT_URL=http://minio:9000` 生成的 presigned URL host 也是 `minio`，
对宿主机访问 `localhost:7910` 的客户端来说 **不可解析**，`302` 会跳到不可达地址。

**本地 docker-compose（mac）建议：**

- MinIO 在 docker network 内：`http://minio:9000`
- 对外（宿主机客户端）暴露：`http://localhost:59000`
- API/Worker 容器内：
  - `YUANTUS_S3_ENDPOINT_URL=http://minio:9000`（内部读写 MinIO）
  - `YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000`（只用于生成 presigned URL，返回给宿主机客户端）

说明：
- `host.docker.internal` 通常只在 **容器内** 可解析，不适合作为“返回给宿主机客户端”的 URL host。

生产私有化建议：

- `YUANTUS_S3_PUBLIC_ENDPOINT_URL` 配成“客户端能访问”的 MinIO 域名（通常经网关/反代，例如 `https://minio.company.local`）

---

## 2) 验收标准（我将按此验证）

### 2.1 Postgres + Alembic（真实迁移）

- 空库下：`yuantus db upgrade` 能创建全部表
- `YUANTUS_SCHEMA_MODE=migrations` 下：**不会自动建表**
- 用 Postgres 跑通 `scripts/verify_run_h.sh`

### 2.2 MinIO(S3) 存储

- `STORAGE_TYPE=s3` 模式下 upload 成功
- `GET /file/{id}/download`：
  - 若走 302：跳转目标 URL 对客户端可达
  - 也可接受“无法 302 时 fallback 流式下载”（如团队决定支持两种策略），但需写清楚行为

### 2.3 Job 并发安全

在 Postgres 上：

- 并行 2 个 worker 处理 10 个 job，不出现重复领取（建议 `SKIP LOCKED` 或原子 claim SQL）

### 2.4 docker compose 一键启动

- `docker compose up --build` 后：
  - 迁移/初始化（bucket）自动完成
  - API `health` 可用
  - 跑通 `scripts/verify_run_h.sh`

---

## 3) 建议的验证命令（示例）

### 3.1 本机跑 API/Worker（docker 仅提供 Postgres/MinIO）

```bash
docker compose up -d postgres minio

export YUANTUS_SCHEMA_MODE=migrations
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL='http://localhost:59000'

yuantus db upgrade
yuantus init-storage

YUANTUS_AUTH_MODE=required yuantus start --port 7910

bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

### 3.2 docker compose 一键（API/Worker 也在容器里）

```bash
docker compose up --build

# API 健康
curl -s http://127.0.0.1:7910/api/v1/health

# Run H 全链路验证（脚本在宿主机执行，调用容器里的 API）
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```
