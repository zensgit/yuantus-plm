# Claude Taskbook: WP1.3 — 2D↔3D 时效一致性(grounding + 设计锁定)

Date: 2026-06-05

Type: **Doc-only grounding/decision taskbook.** WP1.3 比 WP1.1 重一档(碰 `import_batch_id`、`cad_import_service`、`checkin_service`、`VersionFile`/`FileContainer` 时间戳、"过期标志写在哪")。本 taskbook **不写实现**,只把**字段归属、批次来源、状态写入位置、比较口径、API shape、迁移、测试矩阵、排期边界**一次锁死,让随后的实现稳。授权范围:据此开 WP1.3 实现 PR;本 taskbook 自身仅 doc。

Origin: `DEVELOPMENT_WP1_0_CAD_PDM_REPRESENTATION_DECISION_TASKBOOK_20260604.md`(D1:2D↔3D = 文件角色比较)+ `ODOOPLM_BORROW_DEVELOPMENT_PLAN_AND_TODO_20260604.md`(WP1.3)。OdooPLM 参照:`plm/models/ir_attachment.py:1532-1567 assign_must_update_flag()` + `plm/models/plm_dbthread.py`(保存批次防误判)。

---

## 0. What this is(与一句话设计)

把"图纸相对其模型过期"做成 Yuantus 的能力:对**同一 Part**,比较其 `drawing`(2D)文件与 `native_cad`(3D)文件,**用"保存批次"(对应 OdooPLM 的 dbThread)做主信号**判定图纸是否过期;过期标志**物化在图纸侧的 link 行**(`ItemFile`/`VersionFile`),在每次 import/checkin 时重算。**不建任何关系图,不碰 Document Item**(WP1.0 D1)。

**核心反误判规则**:图纸的过期由 **provenance** 判定——图纸 pin 着"上次与它共存保存的模型批次"(`source_batch_id`);仅当模型批次**越过**该 pin 才算过期。**绝不**用"图纸自己的批次 ≠ 模型批次"判过期(批次 id 无序,会假阳)。命门例:save-all 后**仅**重导出 2D,模型没动 → 仍 `up_to_date`(= `plm.dbthread` 防误判)。

---

## 1. Grounding Facts(verified against `main = 700556ac`)

> 全部读码核验,引用 `file:line`。

**F1 · CAD 文件 = `FileContainer`(`meta_files`),且按 checksum 去重(共享!)**
- `src/yuantus/meta_engine/models/file.py:81` `class FileContainer`。
- 时间戳:`created_at`(server_default now)、`updated_at`(onupdate now)、`cad_attributes_updated_at`(`:125`)、`cad_properties_updated_at`(`:130`)、`cad_view_state_updated_at`(`:135`)——**均 `DateTime(timezone=True)`(tz-aware)**。
- **去重**:`CadImportService.import_file`(`services/cad_import_service.py:505-526`)先按 `checksum` 查已存在的 `FileContainer`,命中即**复用**同一行。⇒ **同一物理文件可被多个 Part 共享**;`FileContainer.updated_at` 是"该内容上次被动过"的时间,**不是**"本 Part 这次挂接"的时间。
- 含 `source_file_id`(`:169`,转换产物指回原生件)、`cad_attributes`/`cad_properties`/`cad_view_state`(JSONB)。

**F2 · Part = `Item`;2D 与 3D 都是挂在同一 Part 上的文件(按角色)**
- 角色枚举 `FileRole`(`file.py:34-42`)与 `VersionFileRole`(`version/models.py:29-37`)一致:`native_cad` / `drawing` / `geometry` / `preview` / `attachment` / `reference`。**`drawing`=2D,`native_cad`=3D**。
- `DocumentType`(`file.py:25-31`):`CAD_3D="3d"` / `CAD_2D="2d"` / `pr` / `other`。

**F3 · 两张 link 表(无 batch / 无 staleness 列)**
- `ItemFile`(`meta_item_files`,`file.py:219-247`):`item_id`+`file_id`+`file_role`+`sequence`+`description`+`created_at`。**无 `updated_at`、无批次、无过期标志。**
- `VersionFile`(`meta_version_files`,`version/models.py:155-209`):`version_id`+`file_id`+`file_role`+`sequence`+`snapshot_path`+`is_primary`+`checked_out_by_id/at`;`created_at = datetime.utcnow`(**naive,无 tz!**)。唯一约束 `(version_id, file_id, file_role)`(`:207`)。
- ⇒ **跨 `FileContainer`(aware)与 `VersionFile.created_at`(naive)直接比较时间会出错**;比较必须锚定 `FileContainer` 的 tz-aware 时间。

**F4 · 写入路径**
- 导入:`import_file`(`cad_import_service.py:498`)每次**一文件**:建/复用 `FileContainer` → 可选 `_auto_create_or_update_part`(`:621`)→ `_attach_to_item`(`:696-751`,建/改 `ItemFile`,带 `file_role`)→ `_plan_and_enqueue_jobs`(`:753+`,入队 `cad_preview`/`cad_geometry` 等)。
- `CadImportRequest`(`cad_import_service.py:63-84`)字段:`filename/content/item_id/file_role/.../create_*_job/auto_create_part/...`——**无 `import_batch_id`**(WP1.3 在此新增)。
- 检入:`CheckinManager.checkin(item_id, content, filename)`(`services/checkin_service.py:119-162`)上传 native→`FileContainer`,入队 preview+geometry 作业,再 `VersionService.checkin(properties=props)`。
- 版本文件落地:`VersionFileService.attach_file(version_id, file_id, file_role, is_primary)`(`version/file_service.py:212+`)建 `VersionFile`,`snapshot_path=file.system_path`。⇒ 新增的 link 字段必须在这里一并写。

**F5 · 当前无"保存批次/dbThread"概念**
- `JobService` 的 `dedupe_key`(`models/job.py:50`、`services/job_service.py:28-44`)是**按作业内容去重**,**不是**保存批次/关联 id。⇒ `import_batch_id` 是 WP1.3 **全新引入**的概念,**不复用 dedupe_key**。

**F6 · 单件 staleness 不需要遍历;装配树扫描才需要(排期含义)**
- "某 Part 的图纸 vs 模型"是**同一 item 上两个文件角色**的比较 → **零遍历**。
- "沿装配树扫描过期图纸"需要走 WP1.1 的 `ASSEMBLY` 关系树 = WP1.2 的遍历能力。**但 WP1.0 把 WP1.3 排在 WP1.2 之前。**⇒ 见 §7 排期裁定。

**F7 · checkin 路径与 import 不对齐(必须先抹平,否则 checkin 的模型选不中)**
- `CheckinManager.checkin`(`services/checkin_service.py:119-162`)上传 native 后**只**写 `version.properties["native_file"]=id`(`:123`),**不**建 `file_role=native_cad` 的 `ItemFile`/`VersionFile` 角色行。
- 且 `_CheckinFileService.upload_file`(`:69-84`)硬写 `document_type=DocumentType.OTHER.value`(`:77`)、`checksum=None`(无去重)。
- ⇒ 按 D3 选择器(模型 = `document_type="3d" ∧ file_role="native_cad"` 角色行),**checkin 进来的 3D 原生件既不是 `3d` 也不是角色行,完全选不中**。WP1.3 必须先抹平这条(见 §4「checkin 对齐约束」)。

**F8 · 版本同步会改写既有行(快照可能被污染)**
- `VersionFileService.sync_item_files_to_version`(`version/file_service.py:434`)与 `sync_version_files_to_item`(`:608`)都会 `update` 既有行;`copy_files_to_version`(`:718`)复制。⇒ 若 recompute 无脑同步所有 `VersionFile`,会改掉**历史版本**的 staleness,违背"快照冻结"。见 §4「VersionFile 镜像约束」。

---

## 2. DECISION D1 · 批次来源与形态(`import_batch_id`)

- **来源**:CAD 客户端把"一次保存整套装配"的多文件归为一个批次,通过 **`CadImportRequest.import_batch_id`(opaque string)** 传入;检入侧 `CheckinManager.checkin(..., import_batch_id: Optional[str]=None)`。
- **缺省**:服务端在**一次调用**内若未给 `import_batch_id` 则生成一个(uuid)。⇒ 单文件单独导入 = 各自一个批次(语义正确:它就是独立的一次保存)。
- **不建实体/表**:`import_batch_id` 只是穿过去的属性;**不复用** `JobService.dedupe_key`(F5)。
- **传播**:写到本次创建/更新的 **`ItemFile`** 行;同步到 **`VersionFile`** 快照(经 `attach_file`,F4)。

> 形态锁定:`import_batch_id` 是字符串,可为 client token 或服务端 uuid;**不携带语义**,只用于"同批 = 同一次保存"的相等判断。

---

## 3. DECISION D2 · 字段归属(谁拥有 batch / staleness)

| 候选位置 | 裁定 | 理由 |
|---|---|---|
| `FileContainer`(物理文件) | ❌ **不放** | 按 checksum 去重、跨 Part 共享(F1);放批次/过期会跨件串味、误判 |
| `ItemVersion.properties`(JSONB) | ⚠️ 仅可选缓存 | 无迁移但难扫描/索引;不作主存 |
| **`ItemFile`(item→file link)** | ✅ **主存** | 每个"件上某文件"的挂接是 per-attachment 真相;可加列、可索引 |
| **`VersionFile`(version 快照)** | ✅ **镜像** | 版本快照需冻结当时的批次/过期,供历史核查 |

**新增列(`meta_item_files` 与 `meta_version_files` 各加,additive)**:
- `import_batch_id` (String, nullable, index) —— 该文件行所属保存批次。
- `source_batch_id` (String, nullable) —— **图纸行**记录"上次据以生成/同步的 native_cad 批次"(provenance)。
- `needs_update` (Boolean, default False, index) —— 物化的过期标志(仅 `drawing` 行有意义)。
- `staleness_checked_at` (DateTime(timezone=True), nullable) —— 上次重算时间。
- `staleness_reason` (String, nullable) —— `up_to_date` / `model_moved_on` / `unknown` / `no_model` / `ambiguous`(语义见 §4)。`needs_update=True` ⟺ `staleness_reason="model_moved_on"`。

> 锁定:**batch/staleness 归 link 行,不归 FileContainer。** 扫描靠 `needs_update` 索引(`WHERE needs_update=true`),不做逐读计算。

---

## 4. DECISION D3 · 选择器、provenance 写入与比较口径(核心)

**写在哪**:过期标志物化在**图纸 D(选择器见下)的 `ItemFile`** 行,并镜像到对应当前 `VersionFile`。

**M/D 选择器(确定性,锁定)**:`document_type` 由服务端按扩展名/格式推导(`import_file:554`,可靠);`file_role` 由客户端提供(可能误标)。`document_type` **优先但不独断**——因为 `_get_document_type`(`cad_import_service.py:143-146`)把 `pdf/png/jpg/jpeg` 也归 `"2d"`,而这些常是 `preview`/`printout` 产物,不是图纸。故用 `document_type` 分类 + `file_role` 做**允许集**过滤:
- **模型 M** = `document_type="3d"` **且** `file_role="native_cad"`(在 3D 文件中用 `file_role` 排除 `geometry`/`preview` 衍生件)。
- **图纸 D** = `document_type="2d"` **且** `file_role ∈ {drawing, native_cad}`(**允许集**:`drawing`=正常图纸;`native_cad`=被误标的 2D DWG,见 T13)。**排除** `preview`/`geometry`/`printout`/`attachment`(挡住 PDF printout、PNG/JPG 预览被误当图纸)。
- 多个 native_cad / 歧义配置 → 显式判 `ambiguous`(不猜、不崩)。

**checkin 对齐约束(H1,实现必做)**:WP1.3 实现**必须**让 checkin 路径与 import 对齐——`_CheckinFileService.upload_file`/`CheckinManager.checkin` 要(i)用共享的 `_get_document_type`/`_resolve_cad_metadata` 推导 `document_type`(而非硬写 `OTHER`),且(ii)把 native 模型落成 `file_role=native_cad` 的 `ItemFile`/`VersionFile` **角色行**(而非只塞 `properties["native_file"]`),否则 checkin 的模型 M 选不中(F7)。**测试**:checkin 一个 3D native 后,staleness 服务能把它选作 M(T16)。**✅ 已 ratify(2026-06-05):checkin 抹平对齐为 v0 必做项,checkin 产物纳入 staleness,不排除;T16 为硬性守门。**(不再有"checkin 暂不参与"的备选。)

**provenance 写入规则(关键,补全 advisor 指出的缺口)**:`source_batch_id` 记录"图纸据以构建的**模型**批次",**永远取模型的批次,绝不取图纸自己的**。在 `recompute(item_id)` 中,对每个图纸 D 与当前模型 M:
- 若 `D.import_batch_id == M.import_batch_id`(同一次 save-all)→ 置 `D.source_batch_id = M.import_batch_id`(把图纸 pin 到这次共存的模型批次);
- 否则**保持** D 既有 `source_batch_id`(图纸单独重导**不**改写 provenance)。

**比较口径(纯 provenance 相等,锁定)**:对同一 `item_id`,取 M 与每个 D:
1. 无 M → `no_model`(不判过期)。
2. `D.source_batch_id` 为空(从未与模型共存 / legacy)→ `unknown`(**既不判过期、也不判最新**;留待下次共存保存被 pin)。
3. `D.source_batch_id == M.import_batch_id` → `up_to_date`。
4. `D.source_batch_id != M.import_batch_id`(均非空)→ **stale**(`model_moved_on`):模型已越过图纸所据的批次。

> **为什么不是"批次不等就过期"**:批次 id 是 opaque/无序(D1),两个独立批次 id 不等**不含先后信息**。必须比 provenance(`D.source_batch_id` vs `M.import_batch_id`),**而非**比 `D.import_batch_id` vs `M.import_batch_id`。
>
> **命门反例(必须 not stale)**:save-all 批次 B 同时导入图纸+模型(`D.source_batch_id=B`);随后**仅**重导出 2D 为批次 C(模型未动,仍 B)。则 `D.source_batch_id=B == M.import_batch_id=B` → **up_to_date**。若错用"`D.import_batch_id(=C) ≠ M(=B) ⇒ stale`"就会**假阳**——本设计明确避免。

**时间戳:仅 advisory,不驱动 `needs_update`**。因 `FileContainer` 按 checksum 去重共享、`ItemFile` 无 `updated_at` 且重导只改既有行、`VersionFile.created_at` 为 naive(F1/F3),**时间不是可靠安全网**。API 可附 `time_hint`(取 `FileContainer.updated_at`/`cad_attributes_updated_at` 的 tz-aware 值,仅供人看),但 `needs_update` **只由 provenance 决定**;`unknown` **不**因时间升级为 `stale`。

**何时重算**(对应 OdooPLM checkin/checkout 时 `assign_must_update_flag`):`_attach_to_item`(导入)与 `checkin` 完成后,对该 Part 触发 `CadConsistencyService.recompute(item_id)`(先按上面规则 pin provenance,再算 `needs_update`);并提供按需重算端点(§5)。

**去重防串味**:始终以 per-item 的 link 行/批次为锚,绝不用 `FileContainer` 身份/时间单独判过期(F1)。

**VersionFile 镜像约束(Medium 3,锁定)**:`ItemFile` 是**当前态权威**;`VersionFile` 的这些字段**只在创建/同步当前 version snapshot 时复制冻结**。`recompute` **只写 `ItemFile` + 当前 version 的 `VersionFile`,绝不改非当前/历史版本的 `VersionFile` 行**(否则 `sync_item_files_to_version`/`sync_version_files_to_item`,`file_service.py:434/608` 会把历史快照的 staleness 改掉,违背快照语义,F8)。**测试**:历史版本的 `needs_update`/`source_batch_id` 不被后续 recompute 改写(T15)。

**drawing-only 再生不解除 stale(Medium 4,显式产品语义)**:provenance 只在 `D.import_batch_id == M.import_batch_id`(同批共存)时被 repin。其推论是:模型 B→C 之后,**仅**重导出 2D(批次 ≠ C),即使该图纸确实来自 C,也**不会**清 stale——必须再做一次 2D+3D **同批 save-all** 才解除。**v0 明确接受此约束**:只有同批共存保存能解 stale,drawing-only 再生不 repin。**测试**:模型 `model_moved_on` 后仅重导 2D → **仍 stale**(T14),以免实现者误以为 T2b 覆盖了所有 drawing-only 场景。

---

## 5. DECISION D4 · API shape(item 中心,WP1.0 D4)

- `GET /cad/items/{item_id}/staleness` —— 单件 2D/3D 过期裁定:列出 `drawing` 行 + `needs_update` + `staleness_reason`(provenance 驱动)+ `D.source_batch_id` / `M.import_batch_id` + 只读 `time_hint`(advisory,不驱动判定)。**零遍历。**
- `POST /cad/items/{item_id}/staleness/recompute` —— 强制重算(ops/admin)。
- import/checkin 入参:`CadImportRequest.import_batch_id`(可选);`CheckinManager.checkin(..., import_batch_id=None)`。
- **装配树扫描** `GET /cad/items/{root_id}/stale-drawings?max_depth=N` —— **推迟到 WP1.2 之后**(需 `ASSEMBLY` 遍历,见 §7)。WP1.3 v0 **不**含此端点。
- **禁**:`/documents/{id}/staleness`、任何 DOC_* / Document Item 路径(WP1.0 D4)。
- 命名:服务 `CadConsistencyService`;路由 `cad_consistency_router`(`/cad/items/...`)。

---

## 6. DECISION D5 · 迁移 / 设置 / 事件

- **迁移**:`migrations/` 新增一条 additive 迁移,给 `meta_item_files` + `meta_version_files` 各加 §3 的 5 列(均 nullable/defaulted,**无 backfill**;legacy 行 `source_batch_id=NULL` → 判 `unknown`,见 §4-2)。必要时同步 `migrations_tenant/`。`alembic upgrade head` 须通过。
- **设置**:v0 **无需**新增 `YUANTUS_*`——provenance 相等是精确判断,无容差窗口;`time_hint` 仅展示、不设阈值。**提醒**:若将来给 `time_hint` 加阈值,必须在 `src/yuantus/config/settings.py` 显式声明字段(`extra="ignore"` 会静默丢弃未声明的 `YUANTUS_*`)。勿提前声明无人读的设置(本身就是 no-op 隐患)。
- **事件**:重算导致 `needs_update` 翻转时,经 `events/transactional.enqueue_event` 发一个 `CadDrawingStalenessChangedEvent`(新事件类),勿同步触发副作用。

---

## 7. DECISION D6 · 排期边界(解决 WP1.3 先于 WP1.2 的冲突)

- **WP1.3 v0(本次实现范围)= 单件能力,零遍历**:
  - `import_batch_id` 贯穿 import/checkin + 落 `ItemFile`/`VersionFile`;
  - **checkin 对齐(✅ 已 ratify,必做)**:checkin 推导 `document_type` + 把 native 落成 `file_role=native_cad` 角色行(H1/§4);checkin 纳入 staleness,**T16 守门**;
  - `CadConsistencyService.recompute(item_id)` + 物化 `needs_update`(只写当前态,不碰历史快照);
  - `GET /cad/items/{id}/staleness` + `POST .../recompute`;
  - 迁移 + 事件 + 测试 + CI 登记(v0 无新 `YUANTUS_*`)。
- **装配树扫描 `stale-drawings` → 推迟,依赖 WP1.2 的 `ASSEMBLY` 遍历**。这样保持 WP1.0 的 "WP1.3 先于 WP1.2" 顺序不破:单件 staleness 不需要遍历(F6),先交付;树扫描留到 WP1.2 落地后作为薄封装(`relationship_tree(ASSEMBLY)` × 每件 `needs_update`)。
- 不做 WP3.1 pack-and-go、不改关系类型(WP1.1 已固定)。

---

## 8. 测试矩阵(锁定;`test_cad_2d3d_staleness.py`)

| # | 场景 | 期望 |
|---|---|---|
| T1 | save-all:2D+3D 同一 `import_batch_id` B → recompute pin `D.source_batch_id=B` | `up_to_date` |
| T2 | 模型跨批次重存(`D.source_batch_id=B`,`M.import_batch_id=C`) | **stale**(`model_moved_on`) |
| **T2b** | **命门反例**:save-all(B)后**仅**重导出 2D 为批次 C,模型未动(仍 B) | **`up_to_date`**(不假阳)——核心断言 |
| T3 | `D.source_batch_id` 为空(从未共存 / legacy) | `unknown`(**不** stale、**不** up_to_date) |
| T4 | `unknown` 行存在更晚的 `FileContainer.updated_at`(time_hint) | 仍 `unknown`,`needs_update=False`(时间不升级为 stale) |
| T5 | 无 `native_cad` 行 | `no_model`,不判过期 |
| T6 | recompute 序列:save-all→up_to_date;模型重存→stale;再 save-all(2D+3D)→重新 up_to_date | 状态正确流转 |
| T7 | **去重防串味**:两 Part 共享同一 `FileContainer`,其一改 3D 不污染另一件图纸 | 互不影响 |
| T8 | `needs_update` 翻转发 `CadDrawingStalenessChangedEvent` | 经 enqueue,非同步副作用 |
| T9 | 权限 403 / 异常链 `... from exc` | 通过 |
| T10 | `needs_update` 不依赖 `VersionFile.created_at`(naive);`time_hint` 取 `FileContainer` tz-aware 值 | 无 naive/aware 混用错误 |
| T11 | `import_batch_id` 落 `ItemFile` 并同步到 `VersionFile` 快照 | 两表一致 |
| T12 | 多个 `native_cad`(歧义) | `ambiguous`,不崩 |
| T13 | 选择器:2D DWG 被误标 `file_role=native_cad`(`document_type="2d"`) | 仍归为图纸 D(允许集含 native_cad),**不**被当模型 M |
| **T14** | 模型 `model_moved_on`(B→C)后**仅**重导 2D(批次≠C) | **仍 `stale`**(drawing-only 不 repin,Medium 4) |
| **T15** | recompute 后,**历史版本**的 `needs_update`/`source_batch_id` | **不被改写**(快照冻结,Medium 3) |
| **T16** | checkin 一个 3D native 后 | 能被 staleness 选作模型 M(checkin 对齐,H1) |
| T17 | `document_type="2d"` 的 PDF printout / PNG preview(`file_role=printout`/`preview`) | **不**被当图纸 D(H2 排除集) |

**CI/收尾(静默失败陷阱)**:新测试入 `.github/workflows/ci.yml` contracts 清单(排序正确)+ `conftest.py` allowlist;**v0 不新增 `YUANTUS_*` 设置**(若后续加 `time_hint` 阈值才需入 `config/settings.py`);新 router `include_router` 进 app;迁移 `alembic upgrade head` 通过;新 doc(DEV/V)入 `DELIVERY_DOC_INDEX.md`;`git diff --check` clean。

---

## 9. Explicitly REJECTED

- **批次/过期放 `FileContainer`**:checksum 去重共享 → 跨件串味、误判(F1)。拒绝。
- **用 `VersionFile.created_at` 比较时间**:naive,无 tz,与 `FileContainer`(aware)混用会错(F3)。拒绝;比较一律锚 `FileContainer` tz-aware 时间。
- **"图纸批次 ≠ 模型批次 ⇒ 过期"(比 `D.import_batch_id` vs `M.import_batch_id`)**:批次 id opaque/无序,不等不含先后,会在"仅重导出 2D"时假阳(命门反例,T2b)。拒绝;改比 provenance(`D.source_batch_id` vs `M.import_batch_id`,D3)。
- **以时间戳驱动 `needs_update`**:`FileContainer` 去重共享、`ItemFile` 无 `updated_at`、`VersionFile.created_at` naive(F1/F3)→ 时间不可靠;时间仅作 advisory `time_hint`,**不**驱动过期(D3)。
- **复用 `JobService.dedupe_key` 当批次**:语义是作业去重,非保存批次(F5)。拒绝。
- **WP1.3 内做装配树扫描**:需 WP1.2 遍历;会把 WP1.3 撑大且倒置依赖(F6/D6)。推迟。
- **`document_type="2d"` 独断选图纸**:会把 PDF printout / PNG-JPG preview(也映射成 `2d`)误当图纸(H2)。拒绝;必须叠加 `file_role` 允许集(D3)。
- **无视 checkin/import 不对齐就跑 D3**:checkin 模型 `document_type=OTHER` 且非角色行(F7),会静默选不中。拒绝;先抹平或显式声明 checkin 不参与(§4 约束)。
- **recompute 改历史版本 `VersionFile`**:污染快照(F8/Medium 3)。拒绝;只写当前态。
- **任何 `/documents/...` / DOC_* / Document Item 路径**:违反 WP1.0 D4。拒绝。

---

## 10. Non-Goals

- 不写实现代码/迁移(本 taskbook 仅 doc)。
- 不做 `stale-drawings` 树扫描(WP1.2 后)、不做 pack-and-go(WP3.1)。
- 不改 WP1.1 已固定的 `ASSEMBLY`/`REFERENCE` 关系类型。
- 不实现 CAD 客户端如何产生 `import_batch_id`(由桌面/连接器侧约定;服务端只接收+缺省生成)。

---

## 11. Reviewer Focus

- D2 字段归属:是否同意 batch/staleness 归 **link 行(ItemFile+VersionFile)**、不归 `FileContainer`?
- D3 核心:**provenance 相等**判过期(`D.source_batch_id` vs `M.import_batch_id`)+ `source_batch_id` 仅在"图纸与模型同批共存"时被 pin——是否认可?`unknown`(空 provenance)既不判过期也不判最新,是否符合预期?
- D3 选择器:`document_type` **优先但不独断**——图纸 D = `document_type=2d ∧ file_role∈{drawing,native_cad}`(排除 preview/printout/geometry/attachment,挡 PDF/PNG 误吞,H2);是否认可这个允许集?
- **checkin 对齐(H1,✅ 已 ratify=必做)**:WP1.3 v0 抹平 checkin(推导 `document_type` + 落 `native_cad` 角色行),checkin 纳入 staleness,T16 守门——已定稿,实现照此(无"暂不参与"备选)。
- **快照不被污染(Medium 3)**:recompute 只写当前态、不改历史 `VersionFile`——是否认可?
- **drawing-only 不解 stale(Medium 4)**:只有 2D+3D 同批 save-all 能清 stale,是否接受为 v0 产品语义?
- D4/D6:WP1.3 v0 **不含树扫描**、推到 WP1.2 之后——是否接受?
- D5 迁移:两表各加 5 列(additive、无 backfill);legacy NULL provenance → `unknown` 是否 OK?
- 测试命门:T2b(仅重导出 2D 不假阳)、T7(去重防串味)、T13(误标选择器)是否到位?

---

## 12. Status

- **Decision:** LOCKED(D1–D6)。
- **Ratified (2026-06-05):** H1 = **checkin 抹平对齐**(必做;checkin 纳入 staleness;实现须 derive `document_type` + materialize `native_cad` role row;T16 守门)。无"checkin 暂不参与"备选。
- **Authorizes:** 据此开 **WP1.3 v0 实现 PR**(单件 staleness,无树扫描)。
- **Blocks/defers:** `stale-drawings` 树扫描 → WP1.2 之后。
- **DoD 提醒(实现阶段)**:ci.yml + conftest 双登记;`YUANTUS_*` 入 Settings;迁移三套可 upgrade;事件走 enqueue;异常 `... from exc`;DEV/V 记录入索引。
- **Follow-ups:** B1 状态转换 taskbook(P1,B2 之后);WP1.2 遍历 API;WP3.1 pack-and-go。
