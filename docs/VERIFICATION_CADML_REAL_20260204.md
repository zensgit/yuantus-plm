# CAD ML 本地 + Docker 验证记录 (2026-02-04)

## 目标
- 使用 **本地 cad-ml-platform**（非 Docker）完成 CAD 2D 预览与 OCR 校验
- **重建 cad-ml Docker 镜像**并验证容器健康
- 通过 `scripts/verify_all.sh` 完成回归验证并归档日志

## 本地 cad-ml-platform（非 Docker）

### 启动
```bash
cd /Users/huazhou/Downloads/Github/cad-ml-platform
REDIS_ENABLED=false \
VECTOR_STORE_BACKEND=memory \
DEDUP2D_ASYNC_BACKEND=memory \
GRAPH2D_ENABLED=false \
GRAPH2D_EXCLUDE_LABELS= \
GRAPH2D_ALLOW_LABELS= \
FUSION_ANALYZER_ENABLED=false \
VISION_PROVIDER=stub \
.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8001
```

### 健康检查
```bash
curl -sS http://127.0.0.1:8001/api/v1/vision/health
curl -sS http://127.0.0.1:8001/api/v1/health
```

### 2D 渲染验证（DXF）
```bash
curl -sS -o /tmp/cadml_render.png \
  -F "file=@/Users/huazhou/Downloads/训练图纸/训练图纸/ACAD-布局空白 DXF-2013.dxf" \
  http://127.0.0.1:8001/api/v1/render/cad
```

## Docker 镜像重建 + 健康验证

### 构建镜像
```bash
cd /Users/huazhou/Downloads/Github/cad-ml-platform
docker compose -f deployments/docker/docker-compose.yml build cad-ml-api
```

### 启动容器并检查健康
```bash
CAD_ML_API_PORT=18000 CAD_ML_API_METRICS_PORT=19090 \
  docker compose -f deployments/docker/docker-compose.yml up -d --no-build cad-ml-api redis

curl -sS http://127.0.0.1:18000/api/v1/health
```

### 一键启动验证 (2026-02-05)

```bash
CAD_ML_API_PORT=18000 CAD_ML_API_METRICS_PORT=19090 CAD_ML_REDIS_PORT=16379 \
  scripts/run_cad_ml_docker.sh

curl -sS http://127.0.0.1:18000/api/v1/health
```

结果：`HTTP 200`（status=healthy，redis/ml/api=up）

## 一键脚本（cad-ml Docker）

### 启动
```bash
CAD_ML_API_PORT=18000 CAD_ML_API_METRICS_PORT=19090 CAD_ML_REDIS_PORT=16379 \
  scripts/run_cad_ml_docker.sh
```

### 健康检查
```bash
scripts/check_cad_ml_docker.sh
```

### 停止
```bash
scripts/stop_cad_ml_docker.sh
```

## Yuantus 回归验证（CAD ML 启用）

### 命令
```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 RUN_CONFIG_VARIANTS=1 \
  YUANTUS_AUDIT_ENABLED=true \
  CAD_ML_BASE_URL=http://127.0.0.1:8001 \
  YUANTUS_CAD_ML_BASE_URL=http://127.0.0.1:8001 \
  CAD_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/ACAD-布局空白 DXF-2013.dxf" \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_cadml_20260204-232928.log
```

### 结果
- PASS: 49 / FAIL: 0 / SKIP: 10
- 归档日志：`docs/verification-logs/20260204/verify_all_cadml_20260204_2329.log`

## 关键修复
- `scripts/verify_config_variants.sh`：OptionSet 使用时间戳命名，避免重复运行时 `OptionSet name already exists` 导致的 `KeyError: 'id'`。
