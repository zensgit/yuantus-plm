# P2 ECO Manufacturing Chain Verification Audit

日期：2026-04-18
审计范围：`ECO -> routing/mbom/manufacturing -> release orchestration`

## 目标

在已经完成 `bind_product` 与 `routing change` 两轮 replay 之后，扩大验证面，确认当前 `main` 在 ECO 相邻的 manufacturing / release orchestration 主线上没有新的 runtime 缺口需要继续 replay。

## 背景

前两轮 replay 已分别补回：

- ECO 主链绑定入口
- ECO routing change tracking / routing rebase conflict

接下来的合理动作不是继续围绕同一条已补链条反复重跑，而是扩到 ECO 相邻链，确认是否还存在下一条真实红用例：

- `eco/ecm`
- `routing/mbom/manufacturing/workcenter`
- `release orchestration / release-validation / release-readiness`

本轮结论是：

- 当前 `main` 在扩大后的 focused suites 中均为绿色
- 没有发现新的 `ECO -> manufacturing -> release` runtime 缺口
- 因此本轮不做新的 service/router remediation，只固化验证结果

## 执行过程

### 1. ECO 相邻主链 focused suite

先扩大到：

- `test_eco_*`
- `test_ecm_*`
- `test_routing_*`
- `test_mbom_*`
- `test_manufacturing_*`
- `test_workcenter_*`

执行：

```bash
PYTHONPATH=src python3 -m pytest -q \
  $(rg --files src/yuantus/meta_engine/tests | rg '/test_(eco|ecm|routing|mbom|manufacturing|workcenter)_[^/]+\.py$' | sort)
```

结果：

```text
267 passed, 1 warning in 40.90s
```

### 2. meta_engine 全测试面

进一步扩大到整个 `src/yuantus/meta_engine/tests`：

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests
```

结果：

```text
284 passed, 1 warning in 87.46s (0:01:27)
```

### 3. release-focused 邻接链验证

基于相邻链判断，再单独固定 release orchestration / release-validation 这一层：

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_release_orchestration_router.py \
  src/yuantus/meta_engine/tests/test_release_readiness_router.py \
  src/yuantus/meta_engine/tests/test_release_readiness_export_bundles.py \
  src/yuantus/meta_engine/tests/test_release_validation_directory.py \
  src/yuantus/meta_engine/tests/test_manufacturing_release_diagnostics.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py \
  src/yuantus/meta_engine/tests/test_baseline_release_diagnostics.py
```

结果：

```text
39 passed, 1 warning in 15.57s
```

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
5 passed in 0.01s
```

## 结论

- 当前 `main` 已经覆盖并通过 `ECO -> manufacturing -> release orchestration` 这条扩大后的 focused verification 面
- 本轮没有发现新的 runtime regression，因此不需要额外 replay service/router 变更
- 下一步不应继续在已绿的 `meta_engine` 主链内盲扩；应转向更外层集成面或脚本/CI 合同面寻找下一条真实红用例
