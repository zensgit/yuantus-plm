# Current Worktree Closeout — Merge Readiness (2026-04-25)

## 结论

本次开发批次的代码与验证闭环已收口完成，当前 `main` 可直接按 4 个 PR 分组推进合并流程（`closeout-docs-and-index`、
`closeout-tooling`、`odoo18-verifier-hardening`、`router-decomposition-portfolio`）。

- `git status --short` 仅剩 `?? .claude/`、`?? local-dev-env/`（不纳入提交，按约定本地保留）。
- 当前主线头提交：`c0995a8`（chore: add approvals unregistration closeout doc to delivery index）。
- 目标是“收口即审阅”，不再继续追加新功能开发。

## 4 分组对齐（已落盘）

1. closeout-docs-and-index  
   - 变更入口：`58bf85a`、`be6e3c9`、`56f920f`（含文档、索引、证据补齐）

2. closeout-tooling  
   - 变更入口：`b803bd8`

3. odoo18-verifier-hardening  
   - 变更入口：`a406751`

4. router-decomposition-portfolio  
   - 变更入口：`ce27c48`

> 说明：`55ffae4`、`4777067`、`8c0f6eb`、`c0995a8` 是本批次后续 closeout 与补交接收尾提交的一部分。

## 验证结果（最新复核）

- `bash scripts/print_current_worktree_closeout_commands.sh --commands`  
  - 输出 4 个分组，含对应 `git add` 与审阅命令；
  - 明确排除 `.claude/` 与 `local-dev-env/`。
- `bash scripts/print_current_worktree_closeout_commands.sh --group <group> --commands`（按组核验）：
  - `closeout-docs-and-index`：
    - `git diff --stat -- docs/DELIVERY_DOC_INDEX.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_VERIFIER_HARDENING_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_LOCAL_ONLY_ARTIFACT_INDEX_GUARD_20260425.md src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
    - `git add -- docs/DELIVERY_DOC_INDEX.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_ODOO18_PLM_STACK_VERIFIER_HARDENING_CLOSEOUT_20260425.md docs/DEV_AND_VERIFICATION_LOCAL_ONLY_ARTIFACT_INDEX_GUARD_20260425.md src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - `closeout-tooling`：
    - `git diff --stat -- scripts/print_current_worktree_closeout_commands.sh docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_PR_SPLIT_COMMANDS_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_ROUTER_STAGING_SCOPE_GUARD_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_TOOLING_GROUP_20260425.md .github/workflows/ci.yml`
    - `git add -- scripts/print_current_worktree_closeout_commands.sh docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_current_worktree_closeout_commands.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_PR_SPLIT_COMMANDS_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_ROUTER_STAGING_SCOPE_GUARD_20260425.md docs/DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_TOOLING_GROUP_20260425.md .github/workflows/ci.yml`
  - `odoo18-verifier-hardening`：
    - `git diff --stat -- scripts/verify_odoo18_plm_stack.sh .github/workflows/odoo18-plm-stack-regression.yml .github/workflows/ci.yml docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py`
    - `git add -- scripts/verify_odoo18_plm_stack.sh .github/workflows/odoo18-plm-stack-regression.yml .github/workflows/ci.yml docs/DELIVERY_SCRIPTS_INDEX_20260202.md src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_discoverability.py src/yuantus/meta_engine/tests/test_ci_contracts_verify_odoo18_plm_stack_router_compile.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_change_scope.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_input.py src/yuantus/meta_engine/tests/test_ci_contracts_odoo18_plm_stack_workflow_runtime.py`
  - `router-decomposition-portfolio`：
    - `git diff --stat -- src/yuantus/api/app.py ':(glob)src/yuantus/meta_engine/web/approval*_router.py' ':(glob)src/yuantus/meta_engine/web/box*_router.py' ':(glob)src/yuantus/meta_engine/web/cutted_parts*_router.py' ':(glob)src/yuantus/meta_engine/web/document_sync*_router.py' ':(glob)src/yuantus/meta_engine/web/maintenance*_router.py' ':(glob)src/yuantus/meta_engine/web/quality*_router.py' src/yuantus/meta_engine/web/quality_common.py ':(glob)src/yuantus/meta_engine/web/report*_router.py' ':(glob)src/yuantus/meta_engine/web/subcontracting*_router.py' ':(glob)src/yuantus/meta_engine/web/version*_router.py' ':(glob)src/yuantus/meta_engine/tests/test_approval*_router*.py' src/yuantus/meta_engine/tests/test_approvals_router.py ':(glob)src/yuantus/meta_engine/tests/test_box_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_cutted_parts_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_document_sync*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_maintenance*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_quality*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_report*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_subcontracting*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_version*_router*.py' src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py ':(glob)docs/DEV_AND_VERIFICATION_*ROUTER_DECOMPOSITION*' docs/DEVELOPMENT_CLAUDE_TASK_REPORT_ROUTER_DECOMPOSITION_20260424.md`
    - `git add -- src/yuantus/api/app.py ':(glob)src/yuantus/meta_engine/web/approval*_router.py' ':(glob)src/yuantus/meta_engine/web/box*_router.py' ':(glob)src/yuantus/meta_engine/web/cutted_parts*_router.py' ':(glob)src/yuantus/meta_engine/web/document_sync*_router.py' ':(glob)src/yuantus/meta_engine/web/maintenance*_router.py' ':(glob)src/yuantus/meta_engine/web/quality*_router.py' src/yuantus/meta_engine/web/quality_common.py ':(glob)src/yuantus/meta_engine/web/report*_router.py' ':(glob)src/yuantus/meta_engine/web/subcontracting*_router.py' ':(glob)src/yuantus/meta_engine/web/version*_router.py' ':(glob)src/yuantus/meta_engine/tests/test_approval*_router*.py' src/yuantus/meta_engine/tests/test_approvals_router.py ':(glob)src/yuantus/meta_engine/tests/test_box_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_cutted_parts_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_document_sync*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_maintenance*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_quality*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_report*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_subcontracting*_router*.py' ':(glob)src/yuantus/meta_engine/tests/test_version*_router*.py' src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py ':(glob)docs/DEV_AND_VERIFICATION_*ROUTER_DECOMPOSITION*' docs/DEVELOPMENT_CLAUDE_TASK_REPORT_ROUTER_DECOMPOSITION_20260424.md`
- `bash -n scripts/verify_odoo18_plm_stack.sh`：通过（语法检查通过）
- `bash scripts/verify_odoo18_plm_stack.sh smoke`：`265 passed`
- `bash scripts/verify_odoo18_plm_stack.sh full`：`765 passed`
- pytest（收口核心）：
  - `test_ci_contracts_current_worktree_closeout_commands.py`：1 passed
  - `test_ci_shell_scripts_syntax.py`：18 passed
  - `test_ci_contracts_ci_yml_test_list_order.py`：1 passed
  - `test_ci_contracts_job_wiring.py`：1 passed
  - Odoo18 verifier 套件：5 项共 21 passed
  - 文档索引契约：`test_dev_and_verification_doc_index_completeness.py`、`test_dev_and_verification_doc_index_sorting_contracts.py`、`test_delivery_doc_index_references.py` 全部通过
  - Router 分组 closeout 契约：`test_router_decomposition_portfolio_contracts.py` 5 passed
  - 汇总：共计 `51 passed`（单次命令覆盖 13 个 closeout 核心测试文件）

- 修复跟进：
  - 已在 `docs/DELIVERY_DOC_INDEX.md` 新增本 MD 引用条目；
  - 重新跑上述文档索引契约，确认无 `all docs indexed` 及排序回归。

## 下一步（可直接执行）

1. 打开 4 条 PR（按 group）：
   - `bash scripts/print_current_worktree_closeout_commands.sh --commands`（逐条复制输出中的 `git add` 与 PR 说明）
2. 每条 PR 的 reviewer 重点聚焦在：
   - closeout 文档与索引完整性；
   - helper 契约与脚本语法；
   - Odoo18 verifier 与 router 套件覆盖边界。
3. merge 完成后进入新 cycle 的 gap/需求入口，不再在本分支继续追加新开发功能。

## 非目标（本周期）

- 不在本轮新增功能
- 不改 shared dev 运行时状态
- 不修改未在分组内的未审文件
- 不提交 `.claude/`、`local-dev-env/`
