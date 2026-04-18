# AML Metadata Doc Pack Replay

日期：2026-04-18
接管对象：`#197 docs(aml): add metadata design and verification pack`

## 目标

把 `AML metadata` 文档包从历史 docs 分支 clean replay 到当前 `main`，避免继续沿用挂在旧基线上的开放 PR。

## 背景

- `#197` 仍处于 open 状态
- 它的 GitHub base 仍停在 `main@3e1a00d`
- 当前主线已经推进到后续的 `P2` 观察与 closeout 结果，不适合再直接审旧 PR

本轮改为：

- 从当前 `main` 新切 clean replay 分支
- replay 本地 `codex/aml-metadata-docs-20260411` 上已经拆好的 AML 文档包
- 单独补一份 replay 记录，作为这轮接管与验证证据

## Replay 范围

### Development docs

- `docs/development/README.md`
- `docs/development/aml-metadata-doc-index-20260411.md`
- `docs/development/aml-metadata-federation-design-verification-20260411.md`
- `docs/development/aml-metadata-pact-design-and-verification-20260411.md`
- `docs/development/aml-metadata-session-handoff-20260411.md`

### Index

- `docs/DELIVERY_DOC_INDEX.md`

### Verification note

- `docs/DEV_AND_VERIFICATION_AML_METADATA_DOC_PACK_REPLAY_20260418.md`

## 执行过程

先从当前主线开 replay 分支：

```bash
git switch -c feature/aml-metadata-doc-pack-replay-20260418
```

随后把本地 clean docs 分支上的相关提交 replay 到当前主线分支：

```bash
git cherry-pick 35b30ba^..10e7a75
git cherry-pick b9780d4 d147854
```

实际观察：

- `docs/DELIVERY_DOC_INDEX.md` 在第一轮 cherry-pick 时发生冲突
- 冲突原因是旧 docs 分支和当前主线的索引排序/内容范围已经显著分叉
- 处理方式是保留当前主线版索引，只把 AML 相关路径按当前排序规则补入

## 结果

这轮 replay 后，当前分支相对 `main` 的 AML 文档增量是：

- `docs/development/README.md`
- `docs/development/aml-metadata-doc-index-20260411.md`
- `docs/development/aml-metadata-federation-design-verification-20260411.md`
- `docs/development/aml-metadata-pact-design-and-verification-20260411.md`
- `docs/development/aml-metadata-session-handoff-20260411.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_AML_METADATA_DOC_PACK_REPLAY_20260418.md`

这使得 `AML metadata` 文档包不再依赖旧 `#197` 的历史基线。

## 验证

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

## 关联上下文

- `#197` 是旧的 doc-only PR，base 已陈旧
- 本轮 replay 不改产品 runtime，也不触碰 `P2` frozen remote baseline
- 这是从当前 `main` 继续拆旧混合分支残余价值的第一条 clean docs replay

## 结论

- `AML metadata` 文档包现在可以作为一条独立、可审、可合的 clean replay 分支推进
- 合并后应关闭旧 PR `#197`，改由这条 replay 分支接替
