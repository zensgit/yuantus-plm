# CAD Operator Proof Decision Expiry / Renewal Design

> 日期：`2026-03-22`
> 作用：把 `cad operator proof decision` 从“当前快照绑定的可见动作”升级为“有失效期、有过期告警、有续签闭环”的治理层。

## 1. 目标

让 `POST /api/v1/cad/files/{file_id}/proof/decisions` 成为可被持续管理的 decision contract，而不是一次性动作。

本次实现只补 `cad_router.py` 与其 contract，不新增数据库表，不改模型 schema。

## 2. 参考锚点与超越判断

深读 `references/` 中的实现后，差距明确在于 decision 的生命周期管理缺失：

- DocDoku 通知确认模式是单次确认快照：
  - `ModificationNotificationDTO` 只有 `acknowledged / ackComment / ackAuthor / ackDate`
  - `ModificationNotificationResource` 只做一次性确认
  - 前端 `modification_notification`/`import_status` 主要靠乐观状态写回与文案
- DocDoku import/转换路径没有 decision 与 proof 指纹一致性/过期治理。
- Odoo 的同步/账套 renewal 实现有到期提醒与重试语义（`account_online_synchronization`），但不具备 CAD/BOM proof 指纹绑定。
- Odoo PLM compare 的 wizard/pack-and-go 强在操作闭环，不包含「decision 在新快照下是否失效」的 machine-readable 语义。

Yuantus 的超越点定义为：

- decision 需要在快照（`proof_fingerprint`）上有到期语义。
- expired/missing-expiry 的 decision 会显式要求 operator renew。
- 同一 decision 的后续 renew 使用 `renew_from_decision_id` 显式关联链。
- 决策链路持续进入 export proof bundle，支持审核/交接。

## 3. 现状与落地边界

当前已有基础：

- `GET /api/v1/cad/files/{file_id}/proof`
- `GET /api/v1/cad/files/{file_id}/proof/decisions`
- `POST /api/v1/cad/files/{file_id}/proof/decisions`
- unified bundle 与 `proof_manifest`
- warning/header 与 `audit` 流一致的 `CadChangeLog`

本轮不改动：

- UI 组件（仍保持 API-first）
- 后台 scheduled 决策任务（`renewal scheduler`）
- 外部 reference mirror 的同步策略

## 4. Decision Expiry Contract

新增/更新字段与语义：

- `operator_proof.decision_validity_status`
- `operator_proof.decision_renewal_required`
- `operator_proof.decision_renewal_recommended`
- `operator_proof.active_decision_expires_at`
- `operator_proof.active_decision_expires_in_seconds`
- `active_decision.renewal_required`
- `active_decision.renewal_recommended`
- `active_decision.validity_status`
- `active_decision.renewed_from_decision_id`
- `active_decision.is_superseded`
- `proof_decisions[].expires_at`
- `proof_decisions[].audit_action`
- `proof_decisions[].validity_status`
- `proof_decisions[].expires_in_seconds`
- `proof_decisions[].renew_from_decision_id`

有效期状态定义：

- `active`
  - 有效期存在且未到期。
- `expiring`
  - 未来 `72` 小时内到期（默认窗口）。
- `expired`
  - 已经超过 `expires_at`。
- `missing_expiry`
  - `waived` 决策未填 `expires_at`，认为治理上不完整。
- `no_expiry`
  - `acknowledged` 决策且未设置过期，默认持续有效。

### 4.1 决策治理规则

- `waived` 决策默认要求有 `reason_code`。
- `waived` 决策默认不再允许无截止期；若未设置，`validity_status=missing_expiry` 且 `renewal_required=true`。
- 任何过期或 missing-expiry 的 decision 都会让 `requires_operator_decision=true`。
- 续签动作使用同一 `POST /proof/decisions`，并附带：
  - `renew_from_decision_id`
  - 新 `expires_at`（必须晚于原决策到期）
- 续签成功时 `audit_action` 为：
  - `cad_operator_proof_acknowledgement_renewed`
  - `cad_operator_proof_waiver_renewed`
- 新入参记录 `renewed_from_decision_id`，用于 supersede 关系追溯。
- 新 `proof_fingerprint` 与 `issue_codes` 不一致的旧决策会被标记 `covers_current_proof=false` 或 `is_superseded=true`。

## 5. Bundle / Export 增强

`GET /api/v1/cad/files/{file_id}/bom/export` 导出的 `proof` 和 manifest 增加

- `operator_proof.decision_validity_status`
- `operator_proof.decision_renewal_required`
- `operator_proof.decision_renewal_recommended`
- `proof_manifest.decision_validity_status`
- `proof_manifest.decision_renewal_required`
- `proof_manifest.decision_renewal_recommended`
- `active_decision.validity_status`
- `proof_decisions.csv` 追加字段：
  - `validity_status`
  - `renewal_required`
  - `renewal_recommended`
  - `expires_in_seconds`
  - `renewed_from_decision_id`
  - `audit_action`

`README.txt` 中增加治理字段：

- `decision_validity_status`
- `decision_renewal_required`
- `decision_renewal_recommended`
- `active_decision_id`

## 6. Non-Goals

本轮不改：

- `CAD` 转换算法与 converter 路由
- 全局配置化决策窗口（当前为常量
  `CAD_PROOF_RENEWAL_WINDOW_HOURS=72`）
- 定时任务推送与消息系统事件

## 7. 验证方式

契约测试文件：

- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

关键测试点：

- waiver 必须带 `expires_at`
- waiver 到期后进入 `expired` 且要求续签
- 到期前进入 `expiring`，给出预警动作
- `active_decision` 包含新治理字段
- `GET /proof/decisions` 能反映 `renewed_from_decision_id`
- `POST /proof/decisions` 在续签场景记入 `audit_action`
- ZIP/JSON 证据面可读取 validity 字段
