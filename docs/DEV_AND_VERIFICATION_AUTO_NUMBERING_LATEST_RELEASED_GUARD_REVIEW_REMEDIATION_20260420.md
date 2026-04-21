# DEV AND VERIFICATION - AUTO NUMBERING + LATEST RELEASED GUARD REVIEW REMEDIATION - 2026-04-20

## 背景

针对 `PR #294` 的独立代码审阅，收到了 3 个 merge 前 blocker：

1. `F1` 通用 `/aml/apply` 写入口可通过 nested relationship add 绕过 latest released guard
2. `F2` 自动编号在已有数据库、但 `meta_numbering_sequences` 还是空表时，会从 `1` 起跳，存在历史撞号风险
3. `F4d` `UpdateOperation` 没有同步 `item_number` / `number` 双写，旧客户端只改 `number` 时会出现编号读写漂移

本 remediation 文档只记录这 3 个点的修复，不重复展开主实现目标。主交付文档仍是：

- `docs/DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_20260420.md`

## 修复内容

### 1. `/aml/apply` 旁路补齐 latest released guard

变更：

- `src/yuantus/meta_engine/operations/add_op.py`
- `src/yuantus/meta_engine/web/router.py`

落地方式：

- 在 `AddOperation` 增加 relationship write-time guard
- 覆盖：
  - `Part BOM`
  - `Manufacturing BOM`
  - `Part BOM Substitute`
- guard 位置放在 `on_before_add` 之后，按最终 `related_id` 判定，避免 method hook 改 target 后漏检
- `/aml/apply` 统一把 `NotLatestReleasedError` 映射成 `409 Conflict`

结果：

- latest released guard 不再只存在于显式 `BOMService` / `SubstituteService` 写路径
- 通用 AML nested relationship add 也被兜住

### 2. 自动编号历史 floor bootstrap

变更：

- `src/yuantus/meta_engine/services/numbering_service.py`

落地方式：

- sequence 空表时，不再盲目从 `start=1` 起跳
- 先扫描同 `ItemType` 下已有 `properties.item_number` / `properties.number`
- 解析符合当前 prefix 的历史编号，计算最大已分配值
- insert/upsert 与 generic update 分支都尊重这个 floor
- sequence 落后于历史数据时，会自动追平
- 测试环境若没有 `meta_items` 表，则安全降级为空历史，不影响最小夹具

结果：

- 已有库不会因 sequence 表为空而重新生成 `PART-000001` / `DOC-000001`
- 自动编号上线不会默认引入静默撞号

### 3. update 路径 alias 双写兼容

变更：

- `src/yuantus/meta_engine/operations/update_op.py`

落地方式：

- update 时优先取本次请求里的 `item_number` / `number`
- 再通过 shared helper 同步回两个 alias
- 不再让旧数据里残留的 `item_number` 把本次 legacy `number` 更新覆盖回旧值

结果：

- 旧客户端只改 `number` 时，canonical `item_number` 会同步更新
- 读面不会再出现“写了新编号，但 API 仍返回旧编号”的漂移

## 复审结论

本轮只做了针对性复审，不做全量重审。

复审确认：

- `F1` 已真修到 write path，不是只补 router 文案
- `F2` 已真修到 sequence bootstrap，不是只补测试或注释
- `F4d` 已真修到 update merge 顺序，不是仅靠读路径兼容掩盖问题

## 验证命令

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/operations/tests/test_update_op.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_numbering_service.py

/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

## 验证结果

- code-focused remediation suite: `27 passed`
- docs/index contract suite: `3 passed`

## 对账

悬而未决的 merge 前代码项，到这里已经清空：

- `F1` 已处理
- `F2` 已处理
- `F4d` 已处理

剩余如果还要继续推进，已经不是这 3 个 blocker，而是流程项：

- 是否再单独开 doc-only PR
- 是否对其他 line 做合入后 smoke
