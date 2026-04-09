# YuantusPLM 对标、超越与整体落地计划

> 规划窗口一：`2026-03-21` 到 `2026-06-19`（90 天）
> 规划窗口二：`2026-03-21` 到 `2027-03-20`（12 个月）
> 作用：把 benchmark-driven direction 转成可执行的阶段落地计划。

## 1. 当前状态

截至 `2026-03-21`，整体状态如下：

- `C44/C45/C46` 已稳定在 `main`
- `box`、`document_sync`、`cutted_parts` 已完成一轮 Odoo18-style 并行收口
- benchmark matrix、capability checklist、child checklist template 已具备
- `Aras` scorecard 仍停留在 `2026-02-08` 快照，说明“产品级超越叙事”还缺新一轮证据刷新
- `file-cad` 线当前最小安全下一步已经明确：
  - 以 `GET /api/v1/cad/capabilities` 为唯一正式 autodiscovery contract
  - 为其补直接的 Python contract tests
  - 把 `GET /api/v1/file/supported-formats` 标记为 legacy/deprecated

因此，接下来的整体落地不是继续无边界扩功能，而是按四条并行 lane 推进。

## 2. 90 天落地计划

### Lane A: `file-cad` DocDoku 收口

#### 0-30 天

- canonicalize `GET /api/v1/cad/capabilities`
- 增加 Python router contract tests，覆盖：
  - `connectors`
  - `counts`
  - `formats`
  - `extensions`
  - `features`
  - `integrations`
- 把 `GET /api/v1/file/supported-formats` 标记为 legacy/deprecated

#### 31-60 天

- 评估并补上可选 `cad_bom` contract validation
- 补齐 `cad capabilities` 在 delivery / verification 文档中的引用

#### 61-90 天

- 将 `file-cad` contract convergence 纳入统一回归与交付工件
- 固化为后续 connector / viewer 变更的默认验收入口

#### 交付门槛

- 不修改 upload/conversion/storage 热路径的核心行为
- 有 Python contract tests，而不只靠 shell smoke
- `file-cad` 文档口径与 `DocDoku` 对齐，不再保留 discovery drift

### Lane B: 下一条 Odoo18 bounded increment

这条线默认只允许选择一个 bounded increment，不能重新开启多域并行大批次。

#### 默认候选优先级

1. `checkout gate strictness modes`
2. `breakage grouped counters`
3. `BOM compare mode switch`

#### 0-30 天

- 从三者中固定第一优先级：默认直接采用 `checkout gate strictness modes`
- 在开工前强制创建 benchmark child checklist
- 只允许一个清晰写域，不改热文件

#### 31-60 天

- 完成该 bounded increment 的实现、targeted regression、full regression、merge-prep

#### 61-90 天

- 完成主线稳定窗口
- 只有在该增量稳定后，才允许考虑第二个 bounded increment

#### 交付门槛

- 不得把 `Odoo18` 线重新变成多条业务子域同时扩写
- 必须继续使用 merge-prep + stabilization 模式
- 每次只允许一个 primary benchmark

### Lane C: Aras-facing 产品证据刷新

#### 0-30 天

- 盘点当前 scorecard 对应工件是否过期
- 列出需要刷新的三类证据：
  - strict-gate evidence
  - perf benchmark evidence
  - closed-loop demo / export evidence

#### 31-60 天

- 重新跑或补齐缺失工件
- 更新 closed-loop demo 和 acceptance narrative

#### 61-90 天

- 在有新证据的前提下刷新 `ARAS_PARITY_SCORECARD.md`
- 形成一份可以对外复述的“已对标 / 已领先”证据包

#### 交付门槛

- 没有新证据，不刷新 scorecard 数值
- 所有“超越”描述必须能落回仓库里的验证工件

### Lane D: delivery / ops 硬化

#### 0-30 天

- 把 benchmark child checklist 固化为新 bounded increment 的前置条件
- 复核交付入口文档、runbook、rollback/upgrade 入口是否仍与主线一致

#### 31-60 天

- 把 `file-cad` 和新 bounded increment 的验证入口接入 delivery 文档系统
- 补齐需要的 external verification / operator-facing 手册

#### 61-90 天

- 输出一份“对标到超越”的交付包清单，覆盖：
  - docs
  - scripts
  - verification
  - rollback/upgrade
  - acceptance

#### 交付门槛

- 功能能力和交付能力同步推进
- 不允许功能落地后长期没有对应 delivery 工件

## 3. 12 个月整体阶段

### Phase 1: 稳定对标边界

时间：`2026-03-21` 到 `2026-06-30`

目标：

- 固化 benchmark 分层
- 完成 `file-cad` contract convergence 第一阶段
- 把 Odoo18 并行线切换成单增量 discipline

完成标志：

- `DocDoku` discovery contract 清晰
- 第一个 bounded increment 稳定进入 `main`
- benchmark child checklist 成为默认流程

### Phase 2: 从 breadth 转向 depth

时间：`2026-07-01` 到 `2026-09-30`

目标：

- 把现有主干能力从“已经有”变成“更稳、更强、更易诊断”
- 重点强化读侧、治理、诊断、导出、值班支撑、发布准备度

完成标志：

- 至少再完成一到两个 bounded increments
- 每个增量都具备 merge-prep 和稳定窗口证据
- 不再出现 benchmark 混口径的需求描述

### Phase 3: 强化交付与企业落地

时间：`2026-10-01` 到 `2026-12-31`

目标：

- 把产品能力进一步转化为私有化与企业交付强项
- 强化 runbook、verification、ops diagnostics、release readiness

完成标志：

- 交付包、验证包、演示包形成稳定体系
- plugin / connector / delivery 这三条扩展边界更清晰

### Phase 4: 把 parity 变成可宣称的 surpass

时间：`2027-01-01` 到 `2027-03-20`

目标：

- 不是继续盲扩功能，而是将已有能力压实成领先证据
- 把“可以说自己领先”的部分写成能自证的材料

完成标志：

- scorecard 刷新有新证据支撑
- closed-loop demo / strict-gate / perf / delivery 形成统一证据带
- 至少若干领先点能被准确复述且可复现

## 4. 阶段门禁

每一阶段结束都必须同时通过四类 gate：

### 4.1 Capability Gate

- 新能力或新 contract 已经落地
- benchmark 归属明确

### 4.2 Quality Gate

- targeted regression 通过
- unified full regression 通过
- merge-prep / stabilization 证据齐全

### 4.3 Performance / Ops Gate

- perf benchmark 有最新可复现记录
- strict-gate 或等价日常质量证据可复现
- runbook/diagnostics 没有脱节

### 4.4 Delivery / Evidence Gate

- 文档索引完整
- delivery/verification/acceptance 入口齐全
- 对外叙述与仓库工件一致

## 5. 默认执行顺序

为了避免重新失控，默认顺序固定为：

1. 先做 `file-cad` 的 `cad capabilities` contract convergence
2. 再做一个 Odoo18 bounded increment，默认从 `checkout gate strictness modes` 开始
3. 再刷新 Aras-facing evidence 和 scorecard
4. 同步补齐 delivery / ops 工件

只有在前一项已经达到对应 gate 后，才进入下一项的主推阶段。

## 6. 90 天结束时必须交出的工件

- 一份已收口的 `file-cad` contract 文档与测试证据
- 一个已稳定到 `main` 的 bounded increment
- 一组更新后的 Aras-facing evidence 输入
- 一套同步更新的 delivery / verification / acceptance 文档入口

## 7. 12 个月结束时的验收口径

到 `2027-03-20`，Yuantus 不应以“又补了很多点功能”作为成功标准，而应以以下问题回答为准：

- 机械行业主干闭环是否持续稳定
- bounded increment 机制是否成熟且可复制
- `file-cad` 契约边界是否清晰且可验证
- 私有化交付是否足够强
- “超越 Aras”的叙事是否已有证据，而不是只有方向

只有这些问题都能用仓库工件回答，整体落地计划才算真正完成。

## 8. 关联文档

- `docs/DEVELOPMENT_STRATEGY_PARITY_TO_SURPASS_20260321.md`
- `docs/DEVELOPMENT_DIRECTION_BENCHMARK_DRIVEN_20260321.md`
- `docs/PLAN_ODOO18_PLM_PARALLEL_EXECUTION.md`
- `docs/MERGE_PREP_ODOO18_PLM_STACK_20260319.md`
- `docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md`
- `docs/DESIGN_CAD_CAPABILITIES_ENDPOINT_20260130.md`
