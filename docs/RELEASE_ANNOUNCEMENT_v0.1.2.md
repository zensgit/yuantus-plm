# YuantusPLM v0.1.2 发布公告（模板）

## 发布摘要

- 版本：v0.1.2
- 日期：2026-01-28
- 重点：S12 Configuration/Variant BOM（配置选项集 + BOM 配置过滤）

## 本次亮点

- 新增配置选项集/选项 API（Option Sets / Options）
- BOM 支持 `config_condition` 与 `config` 过滤
- 完整回归已通过（PASS=37, FAIL=0, SKIP=16）

## 验证与文档

- Release Notes：`docs/RELEASE_NOTES_v0.1.2.md`
- Changelog：`CHANGELOG.md`
- 验证汇总：`docs/VERIFICATION_RESULTS.md`

## 快速验证

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

## GitHub Release

- https://github.com/zensgit/yuantus-plm/releases/tag/v0.1.2
