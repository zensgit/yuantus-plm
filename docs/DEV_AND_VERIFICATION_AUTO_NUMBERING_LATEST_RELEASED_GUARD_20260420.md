# DEV AND VERIFICATION - AUTO NUMBERING + LATEST RELEASED GUARD - 2026-04-20

## 目标

在不碰 P1/P2/CAD 主线的前提下，落一个 bounded backend increment：

1. 标准 AML `add` 主链缺号时自动生成 `item_number`
2. BOM child / Substitute / Effectivity 三条写路径只允许消费 latest released target

## 设计选择

### 1. 自动编号

- canonical 字段固定为 `properties.item_number`
- `properties.number` 仅作为兼容镜像，同步写入，避免旧读面分叉
- 读路径兼容统一走共享 helper / 常量，不再散落 `item_number or number`
- 新增 `NumberingService`
- 编号状态持久化到新表 `meta_numbering_sequences`
- 计数实现不走 `max+1`
  - SQLite / PostgreSQL: `INSERT ... ON CONFLICT DO UPDATE` 原子递增
  - 其他方言: insert retry + compare-and-swap update，避免 generic 方言裸奔撞号
- 首版默认仅给 `Part` / `Document` 自动编号
  - `Part` -> `PART-000001`
  - `Document` -> `DOC-000001`
- 显式传入 `item_number` 或 legacy `number` 时不覆盖

### 2. latest released guard

- 新增 `latest_released_guard.py`
- 统一入口：`assert_latest_released(session, target_id, *, context)`
- 自定义异常：`NotLatestReleasedError(reason, target_id)`
- Router 统一映射为 `409 Conflict`
- 判定口径拆开处理 `Item.is_current` 与 `ItemVersion.is_released`
- Effectivity 对 relationship item 的场景先校验 relationship 自身 `is_current`，再校验 `related_id`
- Effectivity 同时传 `item_id` + `version_id` 时双重校验，不能再用 current item 掩盖 stale version

### 3. 回滚开关

- 默认开启
- 支持 settings fallback：`YUANTUS_LATEST_RELEASED_GUARD_DISABLED=true`
- 支持 tenant/org scoped plugin config：
  - `plugin_id=latest-released-guard`
  - `config.disabled=true`

## 改动范围

新增：

- `src/yuantus/meta_engine/models/numbering.py`
- `src/yuantus/meta_engine/services/item_number_keys.py`
- `src/yuantus/meta_engine/services/numbering_service.py`
- `src/yuantus/meta_engine/services/latest_released_guard.py`
- `migrations/versions/e3f4a5b6c7d8_add_numbering_sequences.py`
- `src/yuantus/meta_engine/tests/test_numbering_service.py`
- `src/yuantus/meta_engine/tests/test_latest_released_guard.py`
- `src/yuantus/meta_engine/tests/test_latest_released_write_paths.py`
- `src/yuantus/meta_engine/tests/test_latest_released_guard_router.py`
- `src/yuantus/meta_engine/tests/test_graphql_item_number_alias_contracts.py`
- `docs/DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_20260420.md`

修改：

- `src/yuantus/meta_engine/operations/add_op.py`
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/services/substitute_service.py`
- `src/yuantus/meta_engine/services/effectivity_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `src/yuantus/meta_engine/web/effectivity_router.py`
- `src/yuantus/meta_engine/services/product_service.py`
- `src/yuantus/meta_engine/services/query_service.py`
- `src/yuantus/meta_engine/services/search_service.py`
- `src/yuantus/meta_engine/web/graphql/schema.py`
- `src/yuantus/meta_engine/web/graphql/loaders.py`
- `src/yuantus/meta_engine/web/router.py`
- `src/yuantus/meta_engine/bootstrap.py`
- `src/yuantus/config/settings.py`
- `src/yuantus/meta_engine/operations/tests/test_add_op.py`
- `src/yuantus/meta_engine/operations/tests/test_update_op.py`
- `docs/DELIVERY_DOC_INDEX.md`

## 测试命令

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_graphql_item_number_alias_contracts.py \
  src/yuantus/meta_engine/tests/test_effectivity.py \
  src/yuantus/meta_engine/tests/test_search_service_fallback.py \
  src/yuantus/meta_engine/tests/test_product_detail_service.py \
  src/yuantus/meta_engine/tests/test_product_detail_cockpit_extensions.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

## 测试结果

- 本轮聚焦 + 邻接回归 + docs/index：`48 passed`

覆盖点：

- AddOperation 已接入自动编号
- explicit number 不覆盖
- SQLite 并发下编号单调递增且无重复
- PostgreSQL / SQLite / generic 方言分支已覆盖
- generic 分支的 insert race / conflicting update retry 已覆盖
- latest released 判定覆盖 non-current / unreleased / relationship target
- relationship stale 但 child current 的误放行已补回归
- effectivity 同传 `item_id` + `version_id` 的 stale version 绕过已补回归
- BOM / Substitute / Effectivity 三条写路径都接了 guard
- Router `409` 映射已覆盖
- GraphQL `number` 读面和过滤口径已与 shared helper 对齐
- 本地 venv 未安装 `strawberry`，GraphQL 这轮按源码契约测试验证 helper / filter 接线，不伪装成运行时通过
- migration coverage contract 通过

## 独立审阅后的追加修复

独立审阅指出的 4 个问题，本轮已全部落地：

1. `effectivity_service.create_effectivity()` 之前只校验 `item_id or version_id` 的第一个非空值
   - 已改为两个 target 都校验，避免 current item 掩盖 stale version
2. relationship-target effectivity 之前只看 `related_id`
   - 已改为 relationship 自身先过 `is_current`，再校验 `related_id`
3. `NumberingService` generic 方言之前是 `SELECT -> INSERT/UPDATE` 裸奔
   - 已改为 insert retry + CAS update retry
4. GraphQL 读面之前仍然只认 legacy `number`
   - `schema.py` / `loaders.py` 已统一切到 shared helper / shared filter

## PR 自审 Follow-up

PR `#294` 首轮 CI 中，`contracts` job 失败，原因不是业务逻辑，而是新增的
`src/yuantus/meta_engine/tests/test_graphql_item_number_alias_contracts.py`
未接入 `.github/workflows/ci.yml` 的 `Contract checks` 显式清单。

本轮补丁：

- 将 `test_graphql_item_number_alias_contracts.py` 接入 `CI -> contracts` step
- 本地补跑 workflow wiring / 排序契约，确认没有再引入 CI 清单漂移

这轮 follow-up 不改业务代码，只修 CI wiring。

补充基线说明：

- 额外抽样复跑了 3 个更宽 router 测试：
  - `test_compare_bom_summarized_transforms_rows_and_defaults_to_summarized_mode`
  - `test_version_checkout_passes_when_doc_sync_gate_clear`
  - `test_obsolete_scan_not_found`
- 这 3 个用例在当前 PR worktree 下返回 `401`
- 同样 3 个用例在干净 `origin/main@f001b11` 临时 worktree 下也返回 `401`
- 结论：这批失败是当前主线已有的认证基线问题，不归因本次自动编号 / latest released guard 改动

## 远端 CI 第二轮 Follow-up

`2bc6c8f` 推上去后，PR `#294` 的远端 CI 继续暴露了两类真实夹具问题：

1. `contracts` / Pact provider
   - `add a BOM substitute with optional relationship properties` 从 `200` 变成 `409`
   - 根因：新 guard 生效后，Pact seed 里 BOM/Substitute 消费的 `Part` 只有 `state="Released"`，但没有 `current_version_id + released ItemVersion`
2. `playwright-esign`
   - 多个 BOM / release / workspace spec 在 `POST /api/v1/bom/{parent}/children` 前置失败
   - 根因：这些 spec 直接消费刚创建的 child part；新 guard 要求 child 先成为 latest released

本轮修复全部保持在测试夹具层，不回退业务逻辑：

- `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`
  - 为 `P1`~`P5` 补最小合法 released `ItemVersion`
  - 回写 `Item.current_version_id`
  - 显式将 `Item.updated_at` 置回 `NULL`，保持既有 Pact 响应表面不变
- `playwright/tests/helpers/plmWorkspaceDemo.js`
- `playwright/tests/bom_obsolete_weight.spec.js`
- `playwright/tests/config_variants_compare.spec.js`
- `playwright/tests/product_ui_summaries.spec.js`
- `playwright/tests/release_orchestration.spec.js`
  - 统一把测试 helper 从“直接 promote 到 `Released`”改成真实生命周期路径
  - 兼容 `Draft -> Review -> Released` 与 `Draft -> In Review -> Released`
  - 所有 BOM child / substitute target 在被消费前先走到 latest released

## 第二轮验证命令

Pact provider：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Python focused suite：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_graphql_item_number_alias_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

Playwright targeted rerun：

```bash
npm ci

export BASE_URL=http://127.0.0.1:7910
export PYTHONPATH=src
export YUANTUS_TENANCY_MODE=single
export YUANTUS_DATABASE_URL=sqlite:////tmp/yuantus_playwright.db
export YUANTUS_IDENTITY_DATABASE_URL=sqlite:////tmp/yuantus_playwright.db
export YUANTUS_TEST_FAILPOINTS_ENABLED=true

rm -f /tmp/yuantus_playwright.db
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m yuantus seed-identity \
  --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m yuantus seed-meta
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m uvicorn \
  yuantus.api.app:app --host 127.0.0.1 --port 7910

BASE_URL=http://127.0.0.1:7910 npx playwright test \
  playwright/tests/bom_obsolete_weight.spec.js \
  playwright/tests/config_variants_compare.spec.js \
  playwright/tests/plm_workspace_demo_resume.spec.js \
  playwright/tests/product_ui_summaries.spec.js \
  playwright/tests/release_orchestration.spec.js
```

## 第二轮验证结果

- Pact provider：`1 passed`
- Python focused suite：`29 passed`
- Playwright targeted rerun：`16 passed`

这轮额外确认了两件事：

- latest released guard 没有被回退；问题确实出在旧测试夹具不再满足准入条件
- Playwright seed 环境里的 `Part` 生命周期实际是 `Draft -> Review -> Released`，不是之前假设的直跳 `Released`

## 第三轮 Follow-up：SQLite 并发写锁

`7745050` 推上去后，远端 `playwright-esign` 又暴露了另一类问题：

- 不再是 latest released 语义失败
- 失败日志指向 GitHub Actions 的 SQLite 并发写锁
  - `sqlite3.OperationalError: database is locked`
  - 触发点落在 `promote -> Released` 和 `POST /api/v1/bom/{parent}/children`

这个问题的性质是测试环境瞬时争锁，不是业务判断错误，所以本轮继续只修 Playwright 夹具：

- 新增 `playwright/tests/helpers/sqliteRetry.js`
- 对本次受影响的 `promoteReleased` / `addBomChild` 写请求增加短重试
  - 仅在 `5xx` 或响应体包含 `database is locked` 时重试
  - 最多 3 次，线性退避
  - 不改生产代码，不扩大到其他业务路径

## 第三轮验证命令

本地用与 CI 更接近的并发参数复跑全量 Playwright：

```bash
export BASE_URL=http://127.0.0.1:7910
BASE_URL=http://127.0.0.1:7910 npx playwright test --workers=2
```

## 第三轮验证结果

- Playwright full suite（CI-like, SQLite, `--workers=2`）：`36 passed, 1 skipped`

这轮额外确认：

- `bom_obsolete_weight.spec.js` 的剩余失败确实可由 transient retry 吸收
- 在保留 latest released guard 的前提下，本地全量 Playwright 已恢复为绿
- 远端 `contracts` 已在同一轮 CI 中转绿，说明 Pact 夹具补丁已生效

## 第四轮 Follow-up：审阅 blocker remediation

对 `PR #294` 的独立代码审阅后，又收了 3 个需要在合并前落掉的问题：

1. 通用 `/aml/apply` 写入口仍可通过 nested relationship add 绕过 latest released guard
2. 自动编号在已有数据库、但 `meta_numbering_sequences` 还是空表时，会从 `1` 起跳，存在历史撞号风险
3. `UpdateOperation` 没有同步 `item_number` / `number` 双写，旧客户端只改 `number` 时会出现“写了但读不到新编号”

本轮修复：

- `src/yuantus/meta_engine/operations/add_op.py`
  - 在通用 `AddOperation` 增加 relationship write-time guard
  - 覆盖 `Part BOM` / `Manufacturing BOM` -> `bom_child`
  - 覆盖 `Part BOM Substitute` -> `substitute`
  - 位置放在 `on_before_add` 之后，按最终 `related_id` 判定，避免 method hook 改了 target 后被漏检
- `src/yuantus/meta_engine/web/router.py`
  - `/aml/apply` 新增 `NotLatestReleasedError -> 409` 映射
  - 这样通用 AML 入口与 BOM / Effectivity 专用 router 的冲突语义保持一致
- `src/yuantus/meta_engine/services/numbering_service.py`
  - 新增历史编号 floor 计算
  - sequence 空表时，不再盲目从 `start=1` 起跳，而是先扫描同 `ItemType` 下已有 `item_number/number`
  - generic update 分支也会尊重这个 floor，sequence 落后于真实历史数据时会自动追平
  - 若测试环境尚未建 `meta_items`，floor 计算会安全降级为空历史，不让最小化单测夹具报错
- `src/yuantus/meta_engine/operations/update_op.py`
  - update 时优先取本次请求里的 `item_number/number`，再同步回两个 alias
  - 避免老数据里已有 `item_number` 时，把新传入的 legacy `number` 覆盖回旧值
- focused tests 补充：
  - `test_add_op.py`：新增通用 relationship guard 调用覆盖
  - `test_update_op.py`：新增 alias 双写兼容覆盖
  - `test_latest_released_guard_router.py`：新增 `/aml/apply` -> `409` 覆盖
  - `test_numbering_service.py`：新增历史编号 bootstrap / sequence 落后补齐覆盖

## 第四轮验证命令

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/operations/tests/test_update_op.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_numbering_service.py

/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_graphql_item_number_alias_contracts.py \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/operations/tests/test_update_op.py

/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

## 第四轮验证结果

- add/update focused：`6 passed`
- router/write focused：`9 passed`
- numbering focused：`12 passed`
- broader remediation suite：`36 passed`
- Pact provider：`1 passed`

这轮补完后，最初审阅提出的 3 个 blocker 已全部落地：

- latest released guard 不再只存在于显式 service 写路径，通用 AML nested relationship add 也被兜住
- 自动编号不会在已有库上从 `1` 重新起跳
- canonical `item_number` 与 legacy `number` 的更新兼容被固定住

## 已知边界

- 首版只默认覆盖 `Part` / `Document` 自动编号；其他类型需要在 `ItemType.ui_layout.numbering` 提供规则
- 读面常量本轮显式收敛在 `product_service` / `query_service` / `search_service` / `graphql`
- latest released guard 的 scoped rollback 目前只做 plugin config + settings fallback，没有补单独管理 UI
- Effectivity relationship 场景当前按“relationship 自身 current + related item latest released”处理
- 更宽一圈 BOM summarized / version doc-sync router 测试目前在 `origin/main` 也受统一认证基线影响，未在本 PR 内顺手修 unrelated auth harness

## 结论

这轮交付已经从“任务书”进入“可审 PR”的状态：

- 自动编号不再依赖调用方手工传号
- 写路径上的 latest released 准入从事后扫描前移到了 service 层拦截
- 变更面维持在纯后端 bounded increment，没有顺手扩成 scheduler / UI / router 重构
