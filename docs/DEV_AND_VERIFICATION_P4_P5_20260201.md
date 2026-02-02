# Phase 4/5 基线增强与高级搜索报表 开发与验证（2026-02-01）

## 目标

- Phase 4：基线管理增强（成员、验证、比较、发布、状态字段）。
- Phase 5：高级搜索与可配置报表（保存查询、报表定义、执行记录、仪表板）。

## 关键实现

### 1) 基线管理增强（Phase 4）

- 扩展 `Baseline` 数据结构：增加 baseline_number、scope、state、验证与发布字段、文档/关系包含开关。
- 新增 `BaselineMember`、`BaselineComparison` 表，支持成员快照与基线差异保存。
- `BaselineService` 增强：
  - `create_baseline` 支持成员填充、文档成员、关系成员。
  - `validate_baseline` 完整性校验与验证状态落库。
  - `compare_baselines` 生成差异统计并记录。
  - `release_baseline` 发布+锁定。
- API 增强：
  - `/baselines/compare-baselines`
  - `/baselines/{id}/members`
  - `/baselines/{id}/validate`
  - `/baselines/{id}/release`

### 2) 高级搜索与报表（Phase 5）

- 新增报表与搜索模型：SavedSearch、ReportDefinition、ReportExecution、Dashboard。
- 新增高级搜索服务：支持字段过滤、全文检索、排序与分页。
- 新增保存查询与报表定义服务：
  - 保存查询 CRUD + 运行
  - 报表定义 CRUD + 执行记录
  - 仪表板 CRUD
- API 增强：
  - `/reports/search`
  - `/reports/saved-searches/*`
  - `/reports/definitions/*`
  - `/reports/dashboards/*`

### 3) 迁移

- 迁移文件：`migrations/versions/u1b2c3d4e6a9_add_baseline_reports.py`
- 新增/扩展表：
  - `meta_baselines` 新增字段（状态/验证/发布/范围/编号/包含项）
  - `meta_baseline_members`
  - `meta_baseline_comparisons`
  - `meta_saved_searches`
  - `meta_report_definitions`
  - `meta_report_executions`
  - `meta_dashboards`

## 主要文件

- `src/yuantus/meta_engine/models/baseline.py`
- `src/yuantus/meta_engine/services/baseline_service.py`
- `src/yuantus/meta_engine/web/baseline_router.py`
- `src/yuantus/meta_engine/reports/models.py`
- `src/yuantus/meta_engine/reports/search_service.py`
- `src/yuantus/meta_engine/reports/report_service.py`
- `src/yuantus/meta_engine/web/report_router.py`
- `src/yuantus/meta_engine/bootstrap.py`
- `migrations/versions/u1b2c3d4e6a9_add_baseline_reports.py`

## 验证

### 1) 非 DB 单测

```bash
.venv/bin/pytest -q
```

- 结果：`PASS`（11 passed）
- 记录：`Run PYTEST-NON-DB-20260201-2315`

### 2) DB 启用全量单测

```bash
YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q
```

- 结果：`PASS`（87 passed）
- 记录：`Run PYTEST-DB-20260201-2316`

### 3) SQLite 迁移冒烟

```bash
rm -f /tmp/yuantus_migrate_verify.db && \
  YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db \
  python3 -m alembic -c alembic.ini upgrade head
```

- 结果：`PASS`
- 记录：`Run MIGRATIONS-SQLITE-20260202-0016`

### 4) SQLite 迁移回滚冒烟

```bash
rm -f /tmp/yuantus_migrate_verify.db && \
  YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db \
  python3 -m alembic -c alembic.ini upgrade head && \
  YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_migrate_verify.db \
  python3 -m alembic -c alembic.ini downgrade -1
```

- 结果：`PASS`
- 记录：`Run MIGRATIONS-SQLITE-DOWNGRADE-20260202-0021`

## 备注

- 当前阶段实现覆盖 Phase 4 与 Phase 5 的核心能力；Phase 6 电子签名请见 `docs/DEV_AND_VERIFICATION_P6_ESIGN_20260201.md`。
- 详细结果见 `docs/VERIFICATION_RESULTS.md`。
