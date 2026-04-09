# YuantusPLM 对标、超越与阶段战略

> 日期：`2026-03-21`
> 作用：把 `Aras Innovator`、`Odoo18 PLM`、`DocDoku` 三层 benchmark 收敛成一套“如何对标、如何超越、如何避免跑偏”的统一战略口径。

## 1. 战略基线

截至 `2026-03-21`，Yuantus 当前真实状态是：

- `C44/C45/C46` 已完成主线合并并通过稳定窗口，`box`、`document_sync`、`cutted_parts` 这一轮 Odoo18-style read-side/report/export 收口已经成立
- `Aras` 路线图、`Aras` scorecard、`Odoo18 PLM` 并行执行线、`DocDoku` 文件/CAD 线都已经在仓库中有独立文档
- 真正缺的不是“更多参考对象”，而是把这三层 benchmark 的职责边界、超越定义、以及后续宣称门槛固定下来

因此，这份文档的核心判断是：

- `Aras` 负责“产品级要达到什么”
- `Odoo18 PLM` 负责“当前并行增量怎么做”
- `DocDoku` 负责“CAD / 文件 / connector 体验应该长什么样”

三者不能混为一谈。

## 2. 对标分层

### 2.1 `Aras Innovator` 是产品级北极星

`Aras` 只用于回答这些问题：

- 我们是否覆盖了机械行业主干闭环
- 我们的产品级 parity 处于什么位置
- 我们是否拥有可复现、可宣称的领先能力

这里的核心闭环固定为：

- `Part`
- `BOM`
- `Revision`
- `ECO`
- `Document`
- `CAD`

如果一个需求不能强化这条机械主干闭环，它就不应该被包装成“对标 Aras”的优先事项。

### 2.2 `Odoo18 PLM` 是执行级基线

`Odoo18 PLM` 不是产品北极星，而是当前 `meta_engine` 并行执行的风格基线。

它负责指导：

- 哪些 operations / manufacturing visibility 能力值得做成 bounded increment
- 哪些读侧、报表、导出、状态辅助能力最适合以低冲突方式落地
- 哪些工作应该继续保持隔离域内推进，而不去改热文件

它不负责定义：

- 产品级“已经超越谁”的口径
- CAD / 文件体验的最终边界

### 2.3 `DocDoku` 是 `file-cad` 边界基线

`DocDoku` 只用于指导：

- preview / geometry / metadata / BOM extraction 的契约形态
- connector capability discovery
- conversion microservice 的边界

它不应该被拿来要求 core truth-source 改模，也不应该主导 `box/document_sync/cutted_parts` 这类业务域。

## 3. 什么叫“达到对标”

Yuantus 的 parity 不应该定义为“功能数量看起来差不多”，而应该定义为：

### 3.1 核心闭环完整

至少要能在主干闭环上持续证明：

- 结构完整：`Part/BOM/Revision/ECO/Document/CAD`
- 链路完整：创建、查询、审批、变更、导出、回读、追溯
- 交付完整：文档、脚本、runbook、回归、验收入口齐全

### 3.2 工程证据稳定

不是只把能力写出来，而是要能重复证明：

- strict-gate 可持续
- full-stack 回归可持续
- performance benchmark 可复现
- demo / export / verification bundle 可复现

### 3.3 私有化与运维可落地

对机械行业 PLM 来说，真正的 parity 不只是 API 功能，还包括：

- compose / deployment readiness
- upgrade / rollback / verification runbook
- job / export / release readiness / diagnostics 这类运维侧能力

## 4. 什么叫“超越”

Yuantus 的“超越 Aras”不定义为“无限加功能”，而定义为“在几个仓库已经擅长的维度上，形成可复现领先”。

固定为四类：

### 4.1 证据领先

可以持续产出：

- strict-gate artifacts
- perf benchmark artifacts
- closed-loop demo bundle
- verification script + result pairing

也就是说，超越首先是“更容易证明”，不是“更喜欢讲故事”。

### 4.2 运维与诊断领先

在日常落地里，Yuantus 可以争取领先的方向是：

- cross-domain diagnostics
- export / readiness / cockpit / summary 能力
- 对值班、巡检、恢复、发布准备度更友好的读侧能力

这类能力比“再补一个名词级功能模块”更容易形成真实优势。

### 4.3 扩展与集成领先

`plugin / connector / capabilities contract / conversion microservice` 是 Yuantus 天然更适合强化的方向。

超越的关键不是“支持的系统名单更长”，而是：

- integration contract 更清晰
- autodiscovery 更明确
- private deployment 更容易接入和验证

### 4.4 私有化交付领先

在不少企业场景里，真正形成竞争优势的是：

- 可交付
- 可部署
- 可验证
- 可回滚
- 可审计

这意味着 `delivery docs + runbooks + verification entrypoints + strict/perf evidence` 不是附属品，而是“超越”定义的一部分。

## 5. 超越的宣称门槛

后续任何“Yuantus 已超越 Aras 某能力”的说法，都应该至少同时满足以下四个条件：

1. 有明确的能力边界，不是泛泛口号
2. 有对应的验证入口、回归记录或 demo 工件
3. 有私有化/运维侧可落地证据
4. 有稳定的 benchmark 归属，不混 `Aras/Odoo18/DocDoku`

如果四条做不到，就只能称为“方向”或“潜力”，不能称为“已超越”。

## 6. 非方向

以下路径明确不采用：

- 不把“超越 Aras”当成横向扩 scope 的理由
- 不把 `Odoo18 PLM` 的执行习惯写成产品级长期目标
- 不把 `DocDoku` 的文件/CAD 参考扩展为核心业务建模标准
- 不把外围 CAD/ML/search 服务拉进 core truth-source
- 不把上游参考代码直接视为可复用实现

## 7. 战略优先级

未来 `12` 个月，优先级固定为：

1. 守住机械行业主干闭环
2. 把 Odoo18-style bounded increments 做成稳定交付机制
3. 把 `file-cad` 的 DocDoku contract surface 收口干净
4. 把已有能力转化为可宣称、可交付、可复现的领先证据

也就是说，下一阶段不是“铺更宽”，而是“把已有宽度压成更高质量的可落地深度”。

## 8. 关联文档

- `docs/DEVELOPMENT_ROADMAP_ARAS_PARITY.md`
- `docs/ARAS_PARITY_SCORECARD.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/DEVELOPMENT_DIRECTION_BENCHMARK_DRIVEN_20260321.md`
- `docs/DELIVERY_PLAN_PARITY_TO_SURPASS_20260321.md`
