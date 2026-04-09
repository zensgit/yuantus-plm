# YuantusPLM 参考代码对比与超越矩阵

> 日期：`2026-03-21`
> 作用：把“超越 benchmark / reference code”拆成可执行判断。
> 这里不讨论抽象愿景，只回答四个问题：
> 1. 参考代码当前做到了什么
> 2. Yuantus 当前已经有什么
> 3. 哪些点已经开始领先
> 4. 哪些点还差实现或证据

## 1. 参考锚点

本矩阵基于以下原始或仓库内锚点：

- Odoo checkout / sync
  - `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/ir_attachment.py`
- Odoo BOM compare modes
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
- DocDoku conversion service
  - `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/App.java`
- Yuantus current implementation
  - `src/yuantus/meta_engine/web/version_router.py`
  - `src/yuantus/meta_engine/services/parallel_tasks_service.py`
  - `src/yuantus/meta_engine/web/cad_router.py`
  - `src/yuantus/meta_engine/web/file_router.py`
  - `src/yuantus/meta_engine/services/cad_converter_service.py`
  - `src/yuantus/meta_engine/models/file.py`
  - `docs/RUNBOOK_RUNTIME.md`
  - `docs/REFERENCE_NOTES.md`

## 2. 总结判断

从 reference code 对比看，Yuantus 最可能形成领先的不是“业务面更宽”，而是下面三类：

- 治理更细：从 hard block 变成 soft/hard gate、阈值、上下文并存
- 接入更清：从 scattered integration behavior 变成 canonical discovery contract
- 运维更强：从模块功能变成 operator/readiness/runbook/evidence 一体化

因此，后续的“超越”应该优先围绕：

1. governance
2. autodiscovery
3. readiness
4. evidence

而不是盲目追逐更多模块名词。

## 3. 对比矩阵

| Area | Reference Code | Yuantus Current State | Current Judgment | To Truly Surpass |
| --- | --- | --- | --- | --- |
| Checkout sync gate | Odoo `canCheckOut()` 遇到未同步基本是二元阻断 | `version_router` 已支持 `doc_sync_strictness_mode=block|warn`，并保留阈值与 dead-letter-only policy | `Yuantus` 已在治理细度上开始领先 | 让 `warn` 与 ops summary / release readiness / operator playbook 完整打通 |
| Gate context richness | Odoo 侧主要强调可否 checkout，本体上下文有限 | `parallel_tasks_service` 已产出 `thresholds / blocking_reasons / blocking_counts / blocking_jobs` | `Yuantus` 已明显更适合 operator 排障 | 补固定导出包与真实值班演练证据 |
| CAD capability discovery | DocDoku conversion service 强在转换流程，本身不提供同等级 canonical autodiscovery contract | `GET /api/v1/cad/capabilities` 已统一暴露 connectors / formats / features / integrations | `Yuantus` 已在 integrator clarity 上开始领先 | 增加 degraded/health semantics 和 client integration sample |
| Legacy discovery drift | 传统实现常有多个 discovery surface 并存 | 当前已把 `GET /api/v1/file/supported-formats` 标记为 legacy/deprecated | `Yuantus` 正在收口边界 | 补迁移说明、usage telemetry 或替换验证入口 |
| Conversion pipeline boundary | DocDoku `App.java` 体现 queue listener + temp dir + converter selection + callback + bbox/LOD | `cad_converter_service` 已有 conversion job / viewer readiness / supported conversions，但 bbox/LOD/callback evidence 还不完整 | `Yuantus` 在边界设计上接近，证据上未领先 | 补 bbox/LOD outputs、callback evidence、degraded-mode verification |
| Viewer readiness | 参考代码更偏转换或单点文件可用性，不强调统一 viewer readiness descriptor | Yuantus 已有 `viewer_mode / available_assets / blocking_reasons / is_viewer_ready` | `Yuantus` 在消费侧可解释性上已经更强 | 扩展到大文件/大装配/失败恢复 evidence，避免只停在单元测试 |
| File-derived artifacts model | DocDoku/Odoo 有派生文件与 attachment patterns，但语义分散 | `meta_files` 已统一承载 preview/geometry/document/manifest/metadata/bom/dedup/review | `Yuantus` 在模型组织上有潜在领先 | 把这些字段真正转化为 review/readiness/release API 与 UI contract |
| BOM compare modes | Odoo 已有 `only_product / num_qty / summarized` compare types | Yuantus 当前文档已明确该方向，但主线还未完成相应 bounded increment | 这里仍是 `reference ahead` | 完成 compare mode switch + reason codes + apply-preview safety checks |
| Cross-domain operator cockpit | Odoo/DocDoku 多数按模块提供局部状态 | Yuantus 已有 `parallel-ops` 风格汇总与阈值快照 | `Yuantus` 方向更适合企业值班场景 | 把 cockpit 输出转成固定值班包、导出和 demo evidence |
| Delivery evidence chain | 参考代码通常不等于交付证据体系 | Yuantus 已有 strict-gate / merge-prep / runbook / verification 文档体系 | `Yuantus` 最有机会在这里领先 | 持续刷新新证据，避免只剩历史文档而没有当前工件 |

## 4. 已经开始领先的点

以下几点不是空想，而是仓库里已经有实装或至少已进入 merge-prep 的：

### 4.1 Checkout strictness 比 Odoo 的二元阻断更细

当前 `warn|block` + threshold controls + dead-letter-only policy 的组合，已经比参考 `canCheckOut()` 更接近真实生产治理。

这是一条可以继续放大的领先线。

### 4.2 CAD capabilities contract 比 DocDoku 风格更适合集成

DocDoku 强在 conversion pipeline。
Yuantus 现在更强的方向是让外部 client 一次性知道：

- 支持什么格式
- 什么功能可用
- 哪些集成已配置
- 哪些模式当前能跑

如果把这条合同固定住，Yuantus 在接入细节上是有机会领先的。

### 4.3 Viewer readiness descriptor 是高价值细节优势

`viewer readiness` 不是 benchmark 常见宣传点，但在真实交付里很重要。

它能减少：

- 前端误判
- operator 来回查状态
- support 只能看日志的低效排障

这是典型的“细节领先”。

### 4.4 Delivery evidence 体系本身就是潜在领先点

如果一个系统能稳定给出：

- regression result
- strict-gate result
- runbook
- merge-prep evidence
- verification entrypoint

那它在企业落地里往往会比“只有功能表”的产品更容易成功。

## 5. 还没有领先、但最值得做的点

### 5.1 BOM compare mode switch

这是参考代码里已经很明确、而 Yuantus 还没主线完成的点。

它值得做，不是因为要抄 Odoo，而是因为它属于：

- bounded increment
- UI/compare/reconciliation 都能直接受益
- 交付和验证边界清楚

### 5.2 CAD conversion evidence completeness

DocDoku conversion service 对 queue/temp/callback/converted outputs 这条链路很完整。

Yuantus 设计上已经靠近，但还缺：

- bbox / LOD 明确证据
- callback / external conversion route evidence
- degraded-mode verification

这不是架构问题，而是证据和合同完整度问题。

### 5.3 Warning governance unification

当前仓库已经同时有：

- `X-Quota-Warning`
- `X-Doc-Sync-Checkout-Warning`

如果后续把 warning header、warning code、operator handling policy 做统一，Yuantus 会在“柔性治理”层面形成很强的操作优势。

## 6. 下一步实现优先级

结合当前 merge-prep 状态，建议固定优先级如下：

1. 合并当前 `file-cad` + `checkout gate strictness` merge-prep 分支。
2. 新增一份 operator/integration verification bundle，覆盖：
   - `cad capabilities`
   - `viewer readiness`
   - `checkout warn|block`
3. 把 `BOM compare mode switch` 作为下一条 bounded increment。
4. 补 `cad conversion evidence`：
   - bbox / LOD
   - callback/degraded mode
   - optional `cad_bom` schema validation
5. 统一 warning governance 约定。

## 7. 领先宣称门槛

只有当某一条能力同时满足以下条件时，才适合说“已经超越参考代码”：

1. 参考代码对比点明确
2. 当前实现已经存在，不只是文档
3. 有 direct tests 或 regression evidence
4. 有 operator / integration / delivery 侧的真实收益

如果只满足其中一部分，就只能称为“超越方向成立”，不能称为“已经领先”。

## 8. 结论

Yuantus 不是在所有 benchmark 维度上都已经领先。

但从 reference code 对比看，Yuantus 已经具备形成领先的明确路径，而且这条路径非常具体：

- checkout governance 细度
- CAD autodiscovery clarity
- viewer readiness explainability
- cross-domain operator diagnostics
- delivery evidence strength

只要后续继续用 `bounded increment + direct contract test + runbook + verification evidence` 这套方法推进，Yuantus 在功能、操作、细节三个层面都可以逐步把“对标”压成“可证明的超越”。
