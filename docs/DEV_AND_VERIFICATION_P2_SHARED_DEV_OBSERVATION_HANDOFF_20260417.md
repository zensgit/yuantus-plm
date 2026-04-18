# P2 Shared Dev Observation Handoff

日期：2026-04-17

## 目标

补一份可直接交给共享 dev 环境操作者执行的 handoff 包，避免继续口头说明 `BASE_URL / TOKEN / TENANT_ID / ORG_ID` 和回传物。

这次不伪造共享 dev 结果，只补执行和回传规范。

## 交付

新增：

- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

## 内容

### 1. 打印脚本

`print_p2_shared_dev_observation_commands.sh` 会输出：

- 环境变量模板
- 只读 baseline smoke 命令
- 证据打包命令
- 最小回传文件列表
- 可选 write smoke 命令

### 2. Handoff 文档

`P2_SHARED_DEV_OBSERVATION_HANDOFF.md` 明确：

- 适用范围
- 必备凭证
- 最小执行步骤
- 必须回传的证据
- 可选 write smoke 的前提

## 验证

### 1. Shell syntax

```bash
bash -n scripts/print_p2_shared_dev_observation_commands.sh
```

结果：

- 通过

### 2. Output smoke

```bash
scripts/print_p2_shared_dev_observation_commands.sh
```

结果：

- 正常输出 handoff 命令模板

### 3. Doc index contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

结果：

- 预期通过

## 结论

- 现在即使不把真实凭证直接交给模型，也可以由操作者本地执行 shared dev smoke
- 审阅方只需要接收脚本产物并做结果审阅
