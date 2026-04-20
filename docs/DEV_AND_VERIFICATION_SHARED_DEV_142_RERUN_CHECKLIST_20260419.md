# DEV AND VERIFICATION - Shared-dev 142 Rerun Checklist

日期：2026-04-19

## 背景

`142` 已经完成过 fresh shared-dev first-run，并且真实 observation baseline + after-escalate 回归已经跑通。

后续不再需要重复走 bootstrap；更常见的是：

- 用现有 `$HOME/.config/yuantus/p2-shared-dev.env`
- 在 `142` 上重复跑一次 precheck
- 再跑一次 canonical wrapper

因此这次补的是 **142 专用的常规 rerun 入口**，而不是新的通用 bootstrap 设计。

## 本次改动

- 新增 `docs/P2_SHARED_DEV_142_RERUN_CHECKLIST.md`
- 新增 `scripts/print_p2_shared_dev_142_rerun_commands.sh`
- 更新 `README.md`
- 更新 `docs/DELIVERY_DOC_INDEX.md`
- 更新 `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- 更新 `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- rebase 到最新 `main` 后，保留主线新增的 `142 readonly/workflow` wrappers
- 同步修复 `.github/workflows/ci.yml` 的 contracts wiring，补入 `test_ci_contracts_mainline_baseline_switch_helper.py`

## 验证

执行：

```bash
bash -n scripts/print_p2_shared_dev_142_rerun_commands.sh
bash -n scripts/print_p2_shared_dev_observation_commands.sh
bash scripts/print_p2_shared_dev_142_rerun_commands.sh | sed -n '1,120p'
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py
```

预期：

- 新脚本语法通过
- 打印输出包含 `validate -> precheck -> wrapper` 顺序
- rerun discoverability contract 通过
- CI contracts job wiring / list ordering 通过
- `README` runbooks references/indexing 通过
- 文档索引 completeness / sorting 通过

## 结论

`142` 后续常规 observation rerun 现在有了单独入口，不需要再从 first-run 或更泛的 remote runbook 里拼命令。

在吃进主线新增的 `142 readonly/workflow` wrappers 后，这个入口仍保持 discoverable，并且对应 CI contracts wiring 也已和最新 `main` 对齐。
