# C11 – File/3D Viewer Consumer 超越：开发与验证（2026-03-22）

**Branch**: 当前工作分支（并行开发延续）
**Date**: 2026-03-22
**Status**: 已落地，测试通过

## 1. 变更文件

- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
- `docs/DESIGN_PARALLEL_C11_FILE_VIEWER_CONSUMER_SURPASS_20260322.md`

## 2. 测试

- 目标：`test_file_viewer_readiness.py` 全量回归
- 结果：
  - `36 passed, 27 warnings in 5.98s`
- 关键新增/增强用例覆盖：
  - `proof` 回填（`consumer-summary`、`geometry-pack-summary`、`viewer-readiness/export`）
  - `include_audit=true` 下的 `CadChangeLog` 摘要返回
  - 批量大小校验（空列表、201 条）
  - `export_format` 参数大小写兼容（`CSV` 与 `csv`）
  - CSV 导出的新增列（`history_count`、`history_latest_action` 等）
  - `geometry-pack-summary` 的 `include_assets=false` 行为
  - JSON 导出摘要字段新增：`not_found_count`、`requested_file_count`、`generated_at`
  - `pack-summary` 新增 `not_found_count`
  - `history_limit` 边界（0 值）与消费端审计限制

## 3. 验证命令

```bash
pytest -q src/yuantus/meta_engine/tests/test_file_viewer_readiness.py
```

## 4. 验证结果摘要

- C11 三个接口在默认参数下保持兼容：
  - 仍返回原始 `viewer_mode/is_viewer_ready` 等核心字段
  - 缺失文件继续返回 `not_found`/`found=false` 的宽容行为
- 额外能力仅在 opt-in 参数下生效，避免默认路径性能回退。
- 证据：测试日志中新增 assertions 对照审计、批量上限、CSV 字段全部通过。
