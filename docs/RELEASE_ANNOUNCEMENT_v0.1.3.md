# YuantusPLM v0.1.3 发布公告（模板）

## 发布摘要

- 版本：v0.1.3
- 日期：2026-01-29
- 重点：UI 接入增强 + 配置变体条件扩展

## 本次亮点

- 配置变体条件表达增强（op/exists/missing/范围/正则）
- 产品详情 files[] 别名字段补齐（name/type/role/mime/size/version 等）
- 文档/ECO 摘要新增 items 列表
- BOM UI 输出别名字段补齐（where-used / compare / substitutes）
- UI 联调脚本与清单完备

## 验证与文档

- Release Notes：`docs/RELEASE_NOTES_v0.1.3.md`
- Changelog：`CHANGELOG.md`
- 验证汇总：`docs/VERIFICATION_RESULTS.md`
- UI 联调验证：`docs/VERIFICATION_UI_INTEGRATION_20260129_1329.md`

## 快速验证

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1
```

## GitHub Release

- https://github.com/zensgit/yuantus-plm/releases/tag/v0.1.3
