# 对外交付包说明（2026-02-03）

> 说明：本文档为外部交付材料，不随交付包一起打包。

## 交付物清单

1) 交付包文件（任选其一或同时提供）
- `YuantusPLM-Delivery_20260203.tar.gz`
- `YuantusPLM-Delivery_20260203.zip`

2) 校验文件（与交付包同目录）
- `YuantusPLM-Delivery_20260203.tar.gz.sha256`
- `YuantusPLM-Delivery_20260203.zip.sha256`

3) 外部校验材料（不在交付包内）
- `docs/DELIVERY_PACKAGE_HASHES_20260203.md`（对外哈希清单）
- `docs/DELIVERY_EXTERNAL_VERIFY_COMMANDS_20260203.md`（校验命令合集）

## 推荐交付流程

1) 提供交付包与 `.sha256` 校验文件。
2) 附带本说明与校验命令合集，确保外部接收方能独立完成验证。
3) 提醒接收方在解压后按包内文档验证：
   - `docs/DELIVERY_PACKAGE_MANIFEST_20260203.txt`（包内容清单）
   - `docs/DELIVERY_EXTERNAL_VERIFICATION_GUIDE_20260203.md`（包内验证指引）

## 外部接收方校验步骤（摘要）

1) 校验交付包完整性（对比 `.sha256`）。
2) 解压交付包。
3) 使用包内清单文件进行内容核验。
4) 如需，执行包内脚本进行快速验证。

## 异常处理

- 如校验失败，请停止使用并申请重新下发交付包。
- 如需确认版本，请以 `docs/DELIVERY_PACKAGE_NOTE_20260203.md` 与哈希清单为准。
