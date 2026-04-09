# Reference-Grounded Surpass Backlog

> 日期：`2026-03-21`
> 目标：基于当前仓库实现、主仓库 `references/` 镜像、以及本轮 merge-prep 回归结果，给出一份只保留高价值机会点的“超越对标”待办清单。

## 1. Scope

本清单只看三类参考与实现面：

- Odoo checkout / sync governance
- DocDoku CAD conversion / discovery
- Yuantus operator / readiness / runbook evidence

原始参考锚点：

- `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/ir_attachment.py`
- `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
- `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/App.java`

本轮集成验证上下文：

- `PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-merge-prep-full PYTEST_ADDOPTS='-p no:cacheprovider' scripts/verify_odoo18_plm_stack.sh full`
  - `734 passed, 252 warnings in 15.05s`
- targeted merge-prep pack
  - `python3 -m pytest -q src/yuantus/meta_engine/tests/test_cad_capabilities_router.py src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py`
  - `12 passed, 2 warnings in 11.70s`
- delivery-doc-index contracts
  - `5 passed in 0.07s`
- `bash -n scripts/verify_odoo18_plm_stack.sh`
- `bash -n scripts/verify_docdoku_alignment.sh`
- `PY=/usr/bin/python3 CAD_PREVIEW_ALLOW_FALLBACK=1 bash scripts/verify_docdoku_alignment.sh`
  - failed because local API server `127.0.0.1:7910` was not running, not because of a repository regression

## 2. Ranked Opportunities

### 1. Checkout governance 从“阻断规则”升级为“operator decision surface”

- Benchmark anchor:
  - Odoo `canCheckOut()` 主要是未同步即阻断
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - `src/yuantus/meta_engine/web/version_router.py`
  - `src/yuantus/meta_engine/web/parallel_tasks_router.py`
  - `docs/RUNBOOK_RUNTIME.md`
  - 已有 `block|warn`、dead-letter-only、per-status thresholds、`blocking_reasons`、`blocking_jobs`
- Why this can surpass:
  - Yuantus 已经不只是二元 block，而是更接近面向 operator 的决策上下文
- Still missing:
  - `warn` 模式进入 ops summary / readiness 面
  - per-site policy preset
  - warning telemetry / audit trail
- Best next bounded increment:
  - `doc_sync governance presets + warning telemetry`

### 2. BOM compare 已经从 Odoo wizard 演进成可审计、可导出、可回归能力

- Benchmark anchor:
  - Odoo `compare_bom.py` 提供 `only_product / num_qty / summarized`
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/web/bom_router.py`
  - `src/yuantus/meta_engine/tests/test_bom_summarized_router.py`
  - `src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_router.py`
  - `src/yuantus/meta_engine/tests/test_bom_summarized_snapshot_compare_router.py`
  - 已有 compare modes、summarized snapshot、current-vs-snapshot compare、CSV/Markdown export
- Why this can surpass:
  - 这条线已经不只是“比较”，而是接近“结构差异证据包”
- Still missing:
  - guided apply-preview safety path
  - operator runbook / decision tree
  - demo-grade evidence showing why this is stronger than the wizard model
- Best next bounded increment:
  - `bom compare guided apply-preview + operator evidence`

### 3. CAD autodiscovery contract 可以比 DocDoku 更清楚，但还缺 degraded-state 语义

- Benchmark anchor:
  - DocDoku conversion service 侧重 converter + queue + callback，本身不强调统一 autodiscovery 面
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/web/cad_router.py`
  - `src/yuantus/meta_engine/web/file_router.py`
  - `docs/DESIGN_CAD_CAPABILITIES_ENDPOINT_20260130.md`
  - merge-prep 已把 `GET /api/v1/cad/capabilities` 收口为主 discovery contract，并将 legacy `supported-formats` 标记为 deprecated
- Why this can surpass:
  - 对 UI / connector / deployment 而言，清晰的 autodiscovery contract 比 scattered endpoints 更有价值
- Still missing:
  - health/degraded-state semantics
  - client integration sample
  - usage telemetry proving legacy surface can retire
- Best next bounded increment:
  - `cad capabilities health/degraded contract`

### 4. Viewer readiness / asset transparency 是很强的细节超越点

- Benchmark anchor:
  - 参考代码更偏 conversion success/failure，本仓库里已有更消费侧的 readiness 语义
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/services/cad_converter_service.py`
  - `src/yuantus/meta_engine/web/file_router.py`
  - `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
  - 已有 `viewer_mode`、`available_assets`、`blocking_reasons`、`is_viewer_ready`
- Why this can surpass:
  - 这类语义能直接减少 UI、support、operator 的误判成本
- Still missing:
  - UI/operator 真正消费 readiness contract 的证据
  - large-model / sidecar-failure 演练证据
  - recovery runbook tied to readiness states
- Best next bounded increment:
  - `viewer readiness operator pack`

### 5. CAD conversion 质量证据仍然落后于 DocDoku 的 bbox / LOD / callback 叙事

- Benchmark anchor:
  - DocDoku `App.java` 包含 temp dir、converter selection、bbox、LOD、callback
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/services/cad_converter_service.py`
  - `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
  - `src/yuantus/meta_engine/models/file.py`
  - 代码和文档里已经明确借鉴了 conversion queue / derived asset pattern
- Why this can surpass:
  - 如果把 conversion result 做成可复核的 asset-quality contract，Yuantus 的 explainability 可能更强
- Still missing:
  - bbox / LOD persisted contract
  - callback/result evidence bundle
  - direct tests proving asset-quality metadata stability
- Best next bounded increment:
  - `cad asset quality metadata (bbox/lod/result)`

### 6. CAD BOM contract 是现成的功能延伸点，但还没有验证到“可宣称领先”

- Benchmark anchor:
  - DocDoku 与 CAD connector pipeline 都强调 normalized derived outputs
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
  - `src/yuantus/meta_engine/web/cad_router.py`
  - `src/yuantus/meta_engine/web/file_router.py`
  - `src/yuantus/meta_engine/services/cad_bom_import_service.py`
  - 现有 `cad_bom_path`、下载接口、导入服务、URL 暴露
- Why this can surpass:
  - 如果把 CAD BOM 从“文件结果”升级成“可校验 contract + operator explainability”，就比参考代码更易落地
- Still missing:
  - schema validation
  - nodes/edges contract tests
  - runbook for import failure / mismatch recovery
- Best next bounded increment:
  - `cad_bom schema validation`

### 7. Warning taxonomy 已经出现雏形，但还没统一成平台能力

- Benchmark anchor:
  - 参考实现更多是 hard error / blocking，不强调统一 soft-warning contract
- Yuantus partial implementation:
  - `src/yuantus/meta_engine/web/file_router.py`
  - `src/yuantus/meta_engine/web/cad_router.py`
  - `src/yuantus/meta_engine/web/version_router.py`
  - 已有 `X-Quota-Warning` 与 `X-Doc-Sync-Checkout-Warning`
- Why this can surpass:
  - 统一的 warning contract 能显著提升 operator 和 UI 的降级体验
- Still missing:
  - shared warning schema
  - escalation policy
  - client consumption convention
- Best next bounded increment:
  - `warning contract unification`

### 8. 真正最难也最值钱的超越点，是 evidence pack 而不是单个 endpoint

- Benchmark anchor:
  - 参考代码提供模式，但不会自动给我们 strict-gate / regression / runbook / merge-prep discipline
- Yuantus partial implementation:
  - `scripts/verify_odoo18_plm_stack.sh`
  - `scripts/verify_docdoku_alignment.sh`
  - `scripts/strict_gate.sh`
  - `scripts/strict_gate_report.sh`
  - `docs/RUNBOOK_RUNTIME.md`
  - `docs/DEVELOPMENT_DIRECTION_OPERATIONS_DETAIL_SURPASS_20260321.md`
- Why this can surpass:
  - 企业真实交付里，“更容易证明、更容易回滚、更容易排障”往往比再加一个功能点更有优势
- Still missing:
  - scenario-driven proof bundle
  - stability/perf trend artifacts tied to current branch
  - benchmark-to-evidence trace matrix
- Best next bounded increment:
  - `operator proof bundle`

## 3. What Is Already Strong Enough To Use

当前就可以当成“部分领先基础”的，不需要重新发明：

- `doc_sync` checkout gate 的结构化 context
- `warn|block` API-level strictness
- `cad capabilities` 的统一 discovery shape
- `viewer readiness` 的消费侧语义
- BOM compare summarized snapshots + export
- strict-gate / verify script / runbook 这一整套工程证据方式

## 4. What Should Not Be Claimed Yet

当前还不适合直接对外宣称：

- 已全面超越 `Aras`
- 已全面超越 `DocDoku`
- 已全面超越 `Odoo18 PLM`

更准确的说法应该是：

- Yuantus 已经在若干功能、运维、接入细节上具备形成领先的基础
- 其中部分能力已经出现“比参考实现更适合交付和运维”的趋势
- 但还需要把缺失的 contract / runbook / evidence 补齐，才能从“潜力”升级到“可宣称”

## 5. Default Next Order

默认顺序建议固定为：

1. merge 当前 `file-cad` + `checkout strictness` 分支
2. 做 `cad capabilities health/degraded contract`
3. 做 `cad_bom schema validation`
4. 做 `doc_sync governance presets + warning telemetry`
5. 做 `operator proof bundle`

## 6. Relation To Other Docs

- `docs/DEVELOPMENT_DIRECTION_OPERATIONS_DETAIL_SURPASS_20260321.md`
  - defines the overall operations/details surpass direction
- `docs/REFERENCE_CODE_SURPASS_MATRIX_20260321.md`
  - compares reference anchors against current Yuantus state

This backlog is the execution-oriented follow-up list derived from those two
documents.
