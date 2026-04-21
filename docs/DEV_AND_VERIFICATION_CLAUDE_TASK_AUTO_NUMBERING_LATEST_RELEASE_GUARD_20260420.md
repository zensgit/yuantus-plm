# DEV & Verification: Claude 任务书收敛（自动编号 + 最新已发布约束）2026-04-20

## 1. 目标

把 `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` 中 ROI 最高、最适合下一步并行开发的首个增量，收敛成一份可以直接交给 Claude Code CLI 实施的任务书。

本轮只做任务定义与交付边界固化，不做任何业务代码实现。

## 2. 本轮产出

- 新增任务书：
  - `docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md`
- 同步交付索引：
  - `docs/DELIVERY_DOC_INDEX.md`

## 3. 收敛结果

任务书已把实现范围压缩到一个 bounded increment：

1. 自动部件编号 / 内部编码
2. BOM / Substitute / Effectivity 写路径上的“仅最新已发布版本”准入约束

同时明确排除了以下范围：

- `Suspended` 生命周期态
- scheduler / outbox
- router 巨石拆分
- UI 大改
- P1/P2/CAD 相关主线调整
- 大型 numbering DSL

## 4. 代码现实对齐

为避免任务书基于历史分析文档写错入口，本轮先核对了当前主干真实落点：

- ItemType / Property：`src/yuantus/meta_engine/models/meta_schema.py`
- Item：`src/yuantus/meta_engine/models/item.py`
- AML 主入口：`src/yuantus/meta_engine/services/engine.py`
- Item add 主链：`src/yuantus/meta_engine/operations/add_op.py`
- BOM 写路径：`src/yuantus/meta_engine/services/bom_service.py`
- Substitute 写路径：`src/yuantus/meta_engine/services/substitute_service.py`
- Effectivity 写路径：`src/yuantus/meta_engine/services/effectivity_service.py`
- 生命周期 guard：`src/yuantus/meta_engine/lifecycle/guard.py`
- 版本模型：`src/yuantus/meta_engine/version/models.py`
- release validation 基础件：`src/yuantus/meta_engine/services/release_validation.py`

基于当前代码现实，任务书额外固定了两条实现纪律：

- 自动编号的 canonical 字段必须先收敛，当前优先以 `properties.item_number` 为主。
- latest-released 约束必须走复用 helper，不允许在多个 router/handler 散落硬编码。

## 5. 验证

执行命令：

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：

- `test_dev_and_verification_doc_index_completeness.py`: passed
- `test_dev_and_verification_doc_index_sorting_contracts.py`: passed
- `test_delivery_doc_index_references.py`: passed
- 合计：3 passed

## 6. 附加检查

尝试使用 Claude Code CLI 对任务书做一次非交互歧义扫描，但本机 `claude -p` 在 30 秒窗口内未返回，未形成有效审阅结果。

处理方式：

- 不把这次超时当成验证通过
- 任务书最终由本轮人工复核后保留
- 不影响本轮文档交付与契约测试结论

## 7. 2026-04-20 追补澄清

根据后续人工审阅，本轮又把 5 个实现前高风险歧义补进任务书：

1. 固化编号读路径 fallback 常量，避免 `item_number` / `number` 继续各处分叉。
2. 明确 `NumberingService` 的数据库方言分叉策略，要求 Postgres 与 SQLite 都可用。
3. 固定 latest-released guard helper 的首版接口与异常形状，避免 BOM 接完后再回头改 Effectivity。
4. 明确与 `release_validation.py` 的职责边界，避免误合并成一套 rule registry。
5. 明确 guard 默认启用，但必须预留最小灰度回滚开关，优先复用现有 tenant/org scoped config 或 settings 机制。

这次追补只修改任务书正文，不新增实现范围。

## 8. 已知边界

- 本轮没有实现自动编号功能本身。
- 本轮没有实现 latest-released guard 本身。
- 尚未生成对应业务 PR；当前只是给 Claude 的开发任务书与验收边界。

## 9. 下一步

下一步可以直接把下面文件交给 Claude 作为实现依据：

- `docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md`

待 Claude 产出实现 PR 后，再由 Codex 按 findings-first 方式做正式代码审阅。
