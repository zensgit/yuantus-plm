# CAD Operator Proof Acknowledgement / Waiver Design

> 日期：`2026-03-22`
> 范围：`src/yuantus/meta_engine/web/cad_router.py`
> 目标：把 `CAD operator proof` 从“可看见问题”推进到“可绑定当前 proof 快照、可审计、可导出、可交接的 operator decision trail”。

## 1. Purpose

当前 `GET /api/v1/cad/files/{file_id}/proof` 已经能把下列面统一起来：

- `asset_quality`
- `viewer_readiness`
- `cad_bom summary`
- `cad_bom mismatch`
- `review`
- `history`
- `operator_proof`

但它还缺一个关键治理面：operator 在看到 `needs_review` 或 `blocked` 之后，如何把“谁接受了什么风险、为什么接受、基于哪次 proof 快照接受、这次接受是否仍然覆盖当前 proof”固化成正式 contract。

本设计补的是这条 decision trail，而不是新的 CAD import / convert 功能。

## 2. Reference Grounding

本次设计直接参考并刻意超越下列 reference anchors：

- DocDoku
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ImportPreviewDTO.java`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/PartsResource.java`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/ModificationNotificationResource.java`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ModificationNotificationDTO.java`
- Odoo
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/views/compare_bom_view.xml`
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/pack_and_go_wizard.py`
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/plm_component.xml`

reference 给出的有效模式有两类：

- DocDoku 的 notification acknowledgement 提供了 `ackComment / ackAuthor / ackDate` 这一类最小审计结构。
- Odoo 的 compare/export wizard 提供了强 operator 操作面。

reference 的共同短板也很清楚：

- acknowledgement 语义没有绑定统一 proof surface
- operator decision 没有稳定 machine-readable fingerprint
- 导出更多是结果导出，不是“decision + evidence + current state”一体化导出

Yuantus 这次要超越的正是这一层。

## 3. Existing Ground In Yuantus

仓库里已经有两个足够稳定的基础设施：

1. `CadChangeLog`
   - 路径：`src/yuantus/meta_engine/models/cad_audit.py`
   - 语义：append-only CAD 审计流
2. unified proof bundle
   - 路径：`src/yuantus/meta_engine/web/cad_router.py`
   - 语义：revision-centered `proof` / `bundle` / `export`

因此本设计不引入新表、不引入 migration，也不往 `FileContainer` 增加新的覆盖式 summary 字段。

## 4. New Contracts

### 4.1 `GET /api/v1/cad/files/{file_id}/proof`

在原有 unified proof surface 上新增：

- `operator_proof.proof_fingerprint`
- `operator_proof.decision_status`
  - `open`
  - `acknowledged`
  - `waived`
  - `not_required`
- `operator_proof.requires_operator_decision`
- `operator_proof.has_active_decision`
- `operator_proof.active_decision_id`
- `operator_proof.active_decision_scope`
- `operator_proof.active_decision_covers_current_proof`
- `active_decision`
- `proof_decisions`

这样 operator 不只是看到 proof gap，还能立刻知道：

- 当前是否已经有 decision
- 这个 decision 是否仍然覆盖当前 proof
- 当前 proof 是否需要重新做 acknowledgement / waiver

### 4.2 `GET /api/v1/cad/files/{file_id}/proof/decisions`

新增专门的 decision trail 读取面：

- 返回 `current_fingerprint`
- 返回 `active_decision`
- 返回 `entries`

这个 endpoint 不试图替代 `/history`，而是从通用 CAD history 里提取 proof-governance 子集。

### 4.3 `POST /api/v1/cad/files/{file_id}/proof/decisions`

新增 operator decision 写入面，支持：

- `decision=acknowledged|waived`
- `scope=full_proof|selected_gaps`
- `comment`
- `reason_code`
- `issue_codes`
- `expires_at`

关键约束：

- 当前 `operator_proof.status=ready` 时禁止写 decision
- `waived` 必须带 `reason_code`
- `issue_codes` 必须是当前 proof surface 已知 issue code 的子集

## 5. Persistence Strategy

只复用 `CadChangeLog`，不新增表。

新增 action：

- `cad_operator_proof_acknowledged`
- `cad_operator_proof_waived`

payload 至少保存：

- `decision`
- `scope`
- `comment`
- `reason_code`
- `issue_codes`
- `proof_fingerprint`
- `proof_status`
- `proof_gaps`
- `asset_quality_status`
- `mismatch_status`
- `review_state`
- `expires_at`
- links to `proof` / `proof_decisions` / `export`

这样 decision trail 既能从 `/history` 追，也能被 `/proof` 结构化回读。

## 6. Fingerprint Rule

`proof_fingerprint` 基于当前 operator proof 的关键 technical state 做稳定哈希，至少覆盖：

- `status`
- `asset_quality_status`
- `asset_result_status`
- `converter_result_status`
- `viewer_mode`
- `is_viewer_ready`
- `cad_bom_status`
- `mismatch_status`
- `review_state`
- `proof_gaps`
- `issue_codes`
- `components`
- `file_context`

它的作用不是做安全签名，而是做 operator decision 和当前 proof 快照之间的稳定绑定。

## 7. Bundle / Export Changes

`GET /api/v1/cad/files/{file_id}/bom/export` 的 JSON/ZIP bundle 新增：

- `active_decision.json`
- `proof_decisions.json`
- `proof_decisions.csv`

`proof_manifest.json` 新增：

- `proof_fingerprint`
- `decision_status`
- `requires_operator_decision`
- `proof_decision_count`
- `active_decision_*`

`README.txt` 新增：

- `proof_decisions_url`
- `decision_status`
- `active_decision_id`

这样导出的已经不只是 technical artifact，而是完整 operator proof package。

## 8. Why This Surpasses References

这次超越不是“功能更宽”，而是以下三点同时成立：

1. reference 的 acknowledgement 语义是零散的；Yuantus 的 acknowledgement / waiver 被绑定到 unified proof surface。
2. reference 的 operator decision 很少直接进入 export evidence；Yuantus 的 decision 直接进入 bundle、manifest、README、history。
3. reference 缺少“当前 decision 是否仍覆盖当前 proof”的稳定判断；Yuantus 用 `proof_fingerprint` 把这个判断收成了直接 contract。

## 9. Non-Goals

本次不做：

- 新的 DB 表或 migration
- 新的 UI 页面
- 自动审批流
- decision expiry scheduler
- change log 之外的 denormalized summary column

这些都可以后续再做，但不是本次 bounded increment 的目标。
