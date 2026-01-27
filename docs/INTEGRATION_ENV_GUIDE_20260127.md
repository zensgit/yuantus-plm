# 联测环境一键说明（2026-01-27）

## 目标
将联测过程稳定化：
- 自动识别可运行的可选模块
- 缺失资源时自动降级为 SKIP
- 提供统一入口减少手工环境配置

## 推荐入口
```bash
# 一键联测稳定化入口（自动判断可运行模块）
./scripts/run_integration_stable.sh http://127.0.0.1:7910 tenant-1 org-1
```

该脚本会：
- 自动启用 UI 聚合验收
- 自动启用 S7 Tenant Provisioning / S8 Ops（若平台管理员或审计不可用则内部 SKIP）
- 自动启用 CAD Extractor Stub / Auto Part
- 根据样本文件、覆盖目录、外部服务可达性决定是否启用：
  - CAD 真实连接器（Haochen/Zhongwang）
  - CAD 覆盖率统计
  - CAD Real Samples
  - CAD Extractor External
  - CADGF Preview Online

## 基础环境
```bash
# 基础服务
 docker compose up -d --build
```

多租户模式（db-per-tenant-org）
```bash
docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d --build
```

## 可选组件
### 1) CAD Connector Stub
```bash
# 仅需要 stub 时
 docker compose -f docker-compose.yml -f docker-compose.cad-connector.yml up -d --build
```

### 2) CAD Extractor Service
```bash
# 启动 extractor 微服务
 docker compose --profile cad-extractor up -d cad-extractor
```

### 3) CADGF Router
```bash
# 启动 CADGF router（需要 CADGameFusion 工程）
 ./scripts/run_cadgf_router.sh
```

## 样本路径（可覆盖）
```bash
export CAD_CONNECTOR_COVERAGE_DIR="/path/to/dwg_dir"
export CAD_SAMPLE_DWG="/path/to/sample.dwg"
export CAD_SAMPLE_STEP="/path/to/sample.step"
export CAD_SAMPLE_PRT="/path/to/sample.prt"
export CAD_SAMPLE_HAOCHEN_DWG="/path/to/haocheng.dwg"
export CAD_SAMPLE_ZHONGWANG_DWG="/path/to/zhongwang.dwg"
export CAD_EXTRACTOR_SAMPLE_FILE="/path/to/extractor_sample.dwg"
export CADGF_PREVIEW_SAMPLE_FILE="/path/to/cadgf_preview.dwg"
```

## 常见问题
- **外部服务未启动**：脚本会自动降级为 SKIP，不会阻塞主流程。
- **CADGF Preview Online 失败**：确认 `YUANTUS_CADGF_ROUTER_BASE_URL` 或 `YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL` 已设置。
- **多租户 CLI 失败**：确认 CLI 指向与 API 相同的 Postgres（见 `scripts/run_s7_deep.sh` 说明）。
