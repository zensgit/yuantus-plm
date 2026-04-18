# AML Metadata Provider Contract Replay

日期：2026-04-18
接管对象：`#196 test(pact): verify AML metadata provider contract`

## 目标

把旧基线上的 AML metadata provider contract 变更从历史 PR clean replay 到当前 `main`，并在当前仓库环境上重新完成最小验证闭环。

## 背景

- `#196` 仍处于 open 状态
- 它的 GitHub base 停在旧 `main@3e1a00d`
- 相关 AML metadata 设计文档已经通过后续 clean doc replay 进入主线
- 当前主线仍缺这条 PR 的两个实质性 provider contract 增量：
  - `contracts/pacts/metasheet2-yuantus-plm.json` 里缺少 `GET /api/v1/aml/metadata/Part`
  - `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py` 里缺少 AML metadata verifier 所需的最小 `Property` 种子和新版 Pact verifier 兼容路径

这意味着：

- pact copy 与 `../metasheet2` source-of-truth 存在 drift
- provider verifier 对 AML metadata 交互的覆盖不完整

## Replay 范围

- `contracts/pacts/metasheet2-yuantus-plm.json`
- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
- `docs/DEV_AND_VERIFICATION_AML_METADATA_PROVIDER_CONTRACT_REPLAY_20260418.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 执行过程

先从当前主线开 clean replay 分支：

```bash
git switch -c feature/aml-metadata-provider-contract-replay-20260418
```

先验证当前主线与 Metasheet2 source-of-truth 已经发生 pact drift：

```bash
METASHEET2_ROOT=../metasheet2 \
  bash scripts/sync_metasheet2_pact.sh --check
```

观察到：

```text
pact_sync=drift source_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85 target_hash=03df311fa986b809233553dccc0907457e1aa02cc733ca398d6114ae9401342b
```

随后做两类 clean replay：

### 1. Provider verifier 代码补丁

在 `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py` 补上最小行为差异：

- 导入 `inspect`
- 为 `Part` item type 直接 seed 最小 `Property` rows：
  - `item_number`
  - `name`
  - `description`
  - `state`
  - `cost`
  - `weight`
- 在临时 FastAPI app 上补 `/_pact/provider_states`
- 对新版 `pact.Verifier(..., provider_base_url=...)` 调用方式做兼容

### 2. Pact artifact 同步

不手工编辑 JSON，而是直接用仓库已有同步脚本，从 `../metasheet2` source-of-truth 更新 provider repo copy：

```bash
METASHEET2_ROOT=../metasheet2 \
  bash scripts/sync_metasheet2_pact.sh
```

结果：

```text
pact_sync=updated source_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85 target_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85
```

## 验证

### 1. Pact drift check

```bash
METASHEET2_ROOT=../metasheet2 \
  bash scripts/sync_metasheet2_pact.sh --check
```

结果：

```text
pact_sync=ok source_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85 target_hash=82374b3a8151295c7f419f288eafad382955baa81f6b433eb3874712a8392c85
```

### 2. Provider verifier

仓库里的 `.venv/bin/pytest` shebang 指向失效的旧绝对路径，因此本轮直接使用可工作的虚拟环境解释器执行：

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  -k provider_verifies_local_pacts
```

结果：

```text
1 passed, 3 warnings in 16.24s
```

### 3. 语法检查

```bash
python3 -m py_compile src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

结果：通过。

### 4. 文档索引 contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

结果：

```text
5 passed in 0.02s
```

## 结论

- 当前主线现在重新获得了 AML metadata provider contract 的 committed pact coverage
- Provider verifier 现在能为 AML metadata 交互 seed 出稳定的 `Property` rows
- Pact artifact 不再与 `../metasheet2` source-of-truth 漂移
- 旧 PR `#196` 合并后应关闭，改由这条 clean replay 分支接替
