# DEV AND VERIFICATION - Shared-dev First-run Base Compose

日期：2026-04-19

## 背景

真实 `142` shared-dev 首次执行已经跑通，但执行过程暴露了一个部署入口问题：

- fresh shared-dev first-run 如果直接使用 `docker compose ...`，会隐式加载机器本地 `docker-compose.override.yml`
- 这会把首次初始化路径拖进与本次 bootstrap 无关的外部依赖、宿主机路径和运行时数据库选择

在 `142` 上，最终成功路径实际使用的是：

```bash
docker compose -f docker-compose.yml --env-file ./deployments/docker/shared-dev.bootstrap.env --profile bootstrap run --rm bootstrap
docker compose -f docker-compose.yml up -d api worker
```

因此这次 follow-up 的目标不是追踪某台机器上的 override 内容，而是把 **fresh shared-dev first-run 固定到仓库跟踪的 base compose file**。

## 本次改动

- `scripts/print_p2_shared_dev_first_run_commands.sh`
  - 明确打印 `docker compose -f docker-compose.yml ...`
- `scripts/print_p2_shared_dev_bootstrap_commands.sh`
  - 明确打印 `docker compose -f docker-compose.yml ...`
- `scripts/generate_p2_shared_dev_bootstrap_env.sh`
  - 后续步骤改成 base compose 版本，并明确 first-run 不应依赖机器本地 override
- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
  - 首次初始化命令改成 base compose 版本
- `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md`
  - bootstrap handoff 改成 base compose 版本
- `README.md`
  - Shared-dev bootstrap 段补充 canonical base compose 路径
- `src/yuantus/meta_engine/tests/test_ci_contracts_shared_dev_first_run_base_compose.py`
  - 新增 contract test，防止 first-run 入口退回隐式 compose/override 依赖
- `.github/workflows/ci.yml`
  - 将新的 contract test 纳入 contracts job

## 验证

执行：

```bash
bash -n scripts/print_p2_shared_dev_first_run_commands.sh
bash -n scripts/print_p2_shared_dev_bootstrap_commands.sh
bash -n scripts/generate_p2_shared_dev_bootstrap_env.sh
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_shared_dev_first_run_base_compose.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

预期：

- shell syntax 通过
- 新 contract test 通过
- CI contracts wiring/order 通过
- `DELIVERY_DOC_INDEX.md` development section completeness/sorting 通过

## 结论

fresh shared-dev first-run 现在固定走仓库跟踪的 `docker-compose.yml`，不再隐式依赖机器本地 `docker-compose.override.yml`。
