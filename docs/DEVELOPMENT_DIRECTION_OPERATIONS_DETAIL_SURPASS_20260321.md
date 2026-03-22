# YuantusPLM 操作与细节超越方向

> 日期：`2026-03-21`
> 作用：在既有 benchmark 分层基础上，回答一个更具体的问题: Yuantus 是否能在“操作、落地、细节”层面超越 `Aras Innovator`、`Odoo18 PLM`、`DocDoku`，以及这种超越应该如何被证明。

## 1. 结论

可以，但前提不是继续横向扩功能，而是把仓库里已经具备雏形的几个优势压成稳定、可验证、可交付的能力面。

这里的“超越”不定义为：

- 功能名词更多
- 页面更多
- 参考对象更多

这里的“超越”定义为：

- operator 更容易判断系统当前是否可放行
- integrator 更容易发现系统支持什么、怎么接
- private deployment 更容易验证、回滚、排障
- feature claim 更容易被 regression/runbook/evidence 证明

## 2. 参考材料现状

当前 clean main worktree 并没有顶层 `references/` 目录。

这意味着，在这个 worktree 里能直接复核的 reference material 主要来自三类资产：

- `docs/REFERENCE_NOTES.md`
- `docs/DESIGN_PARALLEL_P3_ODOO18_REFERENCE_PARALLEL_TRACKS_20260306.md`
- 源码里明确标注参考来源的实现与模型

代表性位置包括：

- `docs/REFERENCE_NOTES.md` 里记录的 `DocDoku / ERPNext / Odoo18` 参考路径和设计摘要
- `src/yuantus/meta_engine/models/file.py` 中关于 `DocDoku / Odoo18 / ERPNext` 的模型映射注释
- `src/yuantus/meta_engine/services/cad_converter_service.py` 中关于 `DocDoku-PLM` 与 `Odoo PLM` 的转换服务来源注释
- `docs/DESIGN_DOCDOKU_ALIGNMENT_20260129.md` 中的 CAD/UI contract 映射
- `docs/DESIGN_PARALLEL_P3_ODOO18_REFERENCE_PARALLEL_TRACKS_20260306.md` 中的 Odoo18 并行增量映射

不过，主仓库路径 `/Users/huazhou/Downloads/Github/Yuantus/references` 里的原始参考镜像仍然存在。

本次判断除依赖上述仓库内文档和实现外，还额外抽查了三个原始锚点：

- `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/ir_attachment.py`
- `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
- `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/App.java`

因此，这份文档不是只基于二手摘要，而是结合了：

- clean worktree 里的 reference notes 和 benchmark 文档
- 当前实现里带来源标记的模型与服务代码
- 主仓库 reference mirrors 里的原始参考代码锚点

## 3. 深读后的判断

### 3.1 `Aras` 不擅长指导日常操作细节

`Aras` 适合做产品级闭环和验收北极星，但不适合指导日常“怎么让 operator 更快看懂系统状态”。

这也是为什么 Yuantus 真正有机会超越 `Aras` 的地方，不是在再加一个模块名，而是在：

- operator-facing diagnostics
- release/readiness evidence
- deployment/runbook/verification bundle
- cross-domain warning and soft-gate behavior

### 3.2 `Odoo18 PLM` 给了我们低风险执行切口

Odoo18 reference 真正有价值的，不是直接照搬业务模型，而是它把很多能力切成了小而可交付的增量。

仓库里已经把这条思路落到：

- `doc_sync` checkout gate
- `breakage` grouped counters
- `BOM compare` strategy modes
- `cutted_parts` cadence/alerts/saturation

这意味着 Yuantus 完全可以沿着 Odoo18-style bounded increment 的方式继续推进，但把交付证据和 operator 体验做到更强。

### 3.3 `DocDoku` 给了我们集成边界，而不是产品中心

DocDoku 对 Yuantus 最有价值的是：

- conversion service boundary
- normalized CAD outputs
- preview / geometry / metadata / BOM contract surface
- connector autodiscovery

Yuantus 不需要把 DocDoku 变成产品级总 benchmark，但完全可以在“接入更清晰、诊断更直接、能力暴露更标准”这几个细节上做得更好。

## 4. Yuantus 已经具备的超越抓手

### 4.1 Checkout gate 已经不仅是阻断逻辑，而是 operator 工具

仓库里现有的 `doc_sync` gate 并不只是一个 `409` 判断。

从 `src/yuantus/meta_engine/services/parallel_tasks_service.py` 可以看到，系统已经有：

- threshold snapshot
- threshold hits
- per-status counts
- dead-letter-only policy

从 `docs/RUNBOOK_RUNTIME.md` 可以看到，系统已经把 operator troubleshooting 写成了明确字段：

- `policy`
- `thresholds`
- `blocking_reasons`
- `blocking_counts`
- `blocking_jobs`

再加上这次并行分支里的 `warn|block` strictness mode，Yuantus 的方向已经不是“能不能阻断”，而是“能不能在不丢失上下文的情况下给 operator 一个更柔性的放行判断”。这类操作细节是非常适合超越 benchmark 的。

### 4.2 CAD autodiscovery contract 比传统“文档说明 + 人工配置”更容易落地

`src/yuantus/meta_engine/web/cad_router.py` 已经把 `GET /api/v1/cad/capabilities` 做成了统一 discovery surface：

- connectors
- 2D/3D formats
- extensions
- features
- integrations

这比单纯列接口文档更容易集成，也比把接入逻辑分散在多个端点里更利于私有化交付。

如果继续把 legacy discovery 面收口，并补更多 direct contract tests，Yuantus 在“集成细节”层面完全可以比 benchmark 更清楚。

### 4.3 Viewer readiness 是典型的“细节超越点”

`src/yuantus/meta_engine/services/cad_converter_service.py` 里已经有面向消费侧的 readiness 评估：

- `viewer_mode`
- `geometry_available`
- `manifest_available`
- `preview_available`
- `available_assets`
- `blocking_reasons`
- `is_viewer_ready`

这类接口的价值不在“功能名词”，而在于 operator、前端、集成方可以用统一语义直接判断文件是否 ready。

如果继续把这类 readiness descriptor 扩到更多 CAD/job/export/readiness 场景，Yuantus 在操作细节上会比 benchmark 更可用。

### 4.4 文件模型本身已经为“操作级领先”预留了结构

`src/yuantus/meta_engine/models/file.py` 不只是保存原始文件，它已经覆盖了：

- preview
- geometry
- printout
- `cad_document`
- `cad_manifest`
- `cad_metadata`
- `cad_bom`
- `cad_dedup`
- review state / review note / reviewed_by

这说明 Yuantus 的潜力不在于“再发明一个 CAD 模块”，而在于把已有字段组织成 operator/readiness/review/release 语义更强的界面和 API。

### 4.5 超越最大的空间在“证据化交付”

仓库现在最强的长期优势，不是任何单一 endpoint，而是交付方式：

- strict-gate
- targeted regression
- full-stack verification
- merge-prep discipline
- runbook + verification docs

这套方式一旦稳定下来，Yuantus 最容易形成领先的地方就是：

- 更容易被验证
- 更容易被运维
- 更容易被私有化部署
- 更容易被审计和回滚

这部分是很多 benchmark 产品在本仓库语境下并没有直接给我们的。

## 5. 真正值得超越的操作细节

后续如果要在“操作与细节”层面形成领先，优先级应该固定为：

1. soft gate + hard gate 双模式统一
2. operator-facing readiness / diagnostics / blocking context
3. connector autodiscovery + direct contract verification
4. deploy / rollback / verification package consistency
5. cross-domain summary/export/cockpit 的可解释性

换句话说，超越方向应该是“把 system explainability 做强”，而不是“把抽象模块数量做大”。

## 6. 当前仍然存在的短板

### 6.1 Reference reproducibility 还不够强

`docs/REFERENCE_NOTES.md` 仍然引用了 `references/...` 路径，但当前主线仓库没有这个目录。

这不会阻止我们继续开发，但会削弱两件事：

- deep-read 可复核性
- benchmark 来源的长期可追溯性

后续应该二选一：

1. 恢复只读 reference mirror/submodule
2. 明确把 `REFERENCE_NOTES` 改写成“外部来源摘要”，不要再写成本地存在的路径

### 6.2 `file-cad` 还没有把 DocDoku contract surface 完全收口

`cad capabilities`、`cad_bom summary/review/reimport`、以及 `cad_bom export bundle + runbook` 这三步已经证明，`file-cad` 这条线最适合做“operator-facing contract + evidence package”。

`cad_bom mismatch` 与 `proof bundle` 这一步已经在当前增量里落成，说明
Yuantus 的 CAD operator surface 不只是“能导入”，而是已经能稳定回答
“现在是否漂移、为什么漂移、先导出什么证据”。

当前更值得推进的下一步是：

- 把 `asset_quality`、`viewer readiness`、`cad_bom mismatch` 收口成 unified
  proof surface
- conversion rule / external conversion routing evidence
- mismatch acknowledgement / waiver audit trail

### 6.3 `warn|block` 只是第一步，还不是完整 operator policy 面

现在的 `doc_sync_strictness_mode` 能解决 API 层放行策略，但还没有把 warn 模式和更广的 ops summary / alerting / release readiness 打通。

因此现阶段只能说：

- 已经进入“操作级超越”的正确方向
- 还不能宣称这条能力已经完全领先

## 7. 未来 90 天的最小闭环

如果要把“操作与细节超越”真正做成一条落地线，建议固定为这四步：

1. 把 `cad capabilities`、`viewer readiness`、`cad_bom export bundle`、`checkout gate warn|block` 继续压成统一 operator/integration 验证包。
2. 补一条 reference reproducibility 决策，解决 `references/` 缺位问题。
3. 先完成 `cad asset quality metadata (bbox/lod/result)`，再把它和
   `viewer readiness` / `cad_bom mismatch proof` 链接成统一 proof surface。
4. 在 unified proof surface 完成后，优先补 `acknowledgement / waiver`
   audit trail，而不是继续散开加新 surface。

## 8. 结论

Yuantus 完全有机会在“操作与细节”层面超越 benchmark，但这条路不是“更多功能”，而是：

- 更好的说明力
- 更强的可验证性
- 更清晰的接入契约
- 更稳的 operator 体验

如果后续每个增量都继续沿着 `bounded scope + direct contract test + runbook + verification evidence` 这条路线推进，那么 Yuantus 在很多真实交付场景里，确实有机会比 benchmark 更容易落地、更容易运维，也更容易被证明。

更具体的 reference-by-reference 拆解，见：

- `docs/REFERENCE_CODE_SURPASS_MATRIX_20260321.md`
- `docs/REFERENCE_GROUNDED_SURPASS_BACKLOG_20260321.md`
