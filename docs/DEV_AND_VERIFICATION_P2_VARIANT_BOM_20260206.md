# Development & Verification: Phase 2 Variant BOM (2026-02-06)

## 1. 如何恢复开发进度（对话丢失也不影响）

本项目的“开发进度”以 Git 为准，不依赖对话记录。

- 当前工作分支：`codex/phase2-variant-bom-20260206`
- 当前改动（未提交）：`src/yuantus/meta_engine/services/config_service.py`、`src/yuantus/meta_engine/web/config_router.py`
- 恢复/继续开发的最短路径：
  - `git status -sb` 确认分支与改动
  - `git checkout codex/phase2-variant-bom-20260206`
  - 将未提交改动 commit（可选 push 到远端，确保机器重启/切换电脑也不丢）

## 2. 本次范围（对标路线图 Phase 2）

对照 `docs/DEVELOPMENT_ROADMAP_ARAS_PARITY.md` 的 Phase 2（配置管理/Variant BOM），补齐并验证：

- 配置对比能力：`compare_configurations`
- OptionSet 列表增强：支持按 ItemType 过滤 + 可控包含 global/inactive + 可选展开 options

## 3. 研发内容

### 3.1 后端能力补齐

- 新增 `ConfigService.compare_configurations(...)`：
  - 路径：`src/yuantus/meta_engine/services/config_service.py`
  - 输入：两个 `ProductConfiguration` id
  - 输出：`selection_differences` + 基于有效 BOM 的 `bom_differences`（调用 `BOMService.compare_bom_trees`）
- 新增 API：
  - `POST /api/v1/config/configurations/compare`
  - 路径：`src/yuantus/meta_engine/web/config_router.py`
- 增强 OptionSet 列表 API：
  - `GET /api/v1/config/option-sets`
  - 新增 query params：`item_type_id`、`include_global`、`include_inactive`、`include_options`
  - 兼容性：`include_inactive` 默认 `true`，保持此前行为（之前未提供过滤时会包含 inactive）

### 3.2 自动化测试

- 单元测试（非 DB）：
  - 路径：`src/yuantus/meta_engine/tests/test_config_variants.py`
  - 覆盖：`compare_configurations` 的 selection diff + BOM diff 透传与缺失配置异常
- Playwright API E2E：
  - 路径：`playwright/tests/config_variants_compare.spec.js`
  - 覆盖：创建 OptionSet/Options + VariantRule(modify_qty) + 配置保存 + compare API 返回 selection diff + BOM diff

## 4. 验证记录

### Run PYTEST-NON-DB-20260206-1913

- 时间：`2026-02-06 19:13:58 +0800`
- 命令：`.venv/bin/pytest -q`
- 结果：`PASS`（16 passed）

### Run PYTEST-DB-20260206-1913

- 时间：`2026-02-06 19:13:58 +0800`
- 命令：`YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- 结果：`PASS`（112 passed, 26 warnings）

### Run PLAYWRIGHT-API-20260206-1913

- 时间：`2026-02-06 19:13:58 +0800`
- 命令：`npx playwright test`
- 结果：`PASS`（5 passed, 1 skipped）
- 说明：`playwright/tests/cad_preview_ui.spec.js` 默认跳过，需要 `RUN_PLAYWRIGHT_CAD_PREVIEW=1`

