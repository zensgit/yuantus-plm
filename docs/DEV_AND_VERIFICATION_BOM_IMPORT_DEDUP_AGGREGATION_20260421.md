# DEV_AND_VERIFICATION_BOM_IMPORT_DEDUP_AGGREGATION_20260421

## 1. 目标

在 `CadBomImportService.import_bom` 的 commit 边界前，按 `(parent_item_id, resolved_child_item_id, normalized_uom)` 对 BOM edges 做去重聚合：

- 同 key 多行 → 合并为一行，`quantity` 累加；`find_num` 保留首个非空值；`refdes` 跨 edge 合并、去重并稳定排序。
- 不同 uom（或不同 parent / child）保持独立行。
- 聚合后的统一结果再交给 `BOMService.add_child` 写库。

同时把 uom 归一化成大写 stripped 形式（未提供时默认 `EA`），确保 `"mm"` / `"MM"` / `" mm "` 聚合到同一 key 且最终存储形式一致。

## 2. 范围

### 2.1 改动

- `src/yuantus/meta_engine/services/cad_bom_import_service.py`
  - 新增模块级 helper `_normalize_uom(value, *, default="EA") -> str`，复用 `_normalize_text` 做 None/空串处理后再 `.upper()`。
  - 新增模块级 helper `_refdes_tokens(value) -> List[str]`：支持 list/tuple/set/comma-separated 字符串输入，拆分 + strip + 过滤空值与 `None`，保留输入顺序。
  - 新增模块级 helper `_join_refdes_tokens(tokens) -> Optional[str]`：按 lexicographic 稳定排序 + 去重 + comma join，全空返回 `None`。
  - `CadBomImportService.import_bom` 的 `for edge in edges:` 循环从「逐行 add_child」重构为两阶段：
    - **Phase 1 · 聚合**：遍历 edges，按 `(parent_item_id, child_item_id, normalized_uom)` 建 dict；重复 key 的 `quantity` 累加，`find_num` **保留首个非空**（不合并），`refdes` 累积所有 token 到 `set`。记录 `aggregation_order` 保持首次出现顺序。
    - **Phase 2 · Commit**：按 `aggregation_order` 迭代，对 refdes token set 调 `_join_refdes_tokens` 得到稳定排序 + 去重的 comma-separated 字符串，调一次 `self.bom_service.add_child(...)`。
  - 返回结果 dict 新增 `dedup_aggregated: int` 字段，表示被合并的行数（不包括保留的首行）。
- `src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py`（**新增**）：19 个测试覆盖（3 个 `_normalize_uom` 单元 + 4 个 `_refdes_tokens` / `_join_refdes_tokens` 单元 + 11 个 `import_bom` integration + 1 个 real-session SQLite）。
- `docs/DEV_AND_VERIFICATION_BOM_IMPORT_DEDUP_AGGREGATION_20260421.md`（本 MD）。
- `docs/DELIVERY_DOC_INDEX.md`：新增本 MD 索引项。

### 2.2 不改动（硬边界）

- **不**碰 scheduler 相关文件（`scheduler_service.py` / `scheduler_tasks.py` / compose scheduler profile / settings 里的 `SCHEDULER_*`）
- **不**碰 CAD backend profile 相关（`cad_backend_profile_service.py` / `/cad/backend-profile` 端点 / `CAD_STEP_IGES_BACKEND` 设置）
- **不**动 shared-dev 142 任何 artifact（脚本 / 远端配置 / 142 runbook）
- **不**改 UI（HTML / JS / web 路由 / workbench / plm_workspace）
- **不**新增 schema / migration
- **不**改 `BOMService.add_child` 签名或行为
- **不**改 `_normalize_text` / `_normalize_refdes` / `_parse_quantity` 既有语义

## 3. 设计决策

### 3.1 聚合 key 为什么包含 parent

用户原始口径是「(resolved child item_id or item_number, normalized uom)」，但多层 BOM 中同一个子件出现在不同父件下**是合法的不同 BOM 行**（e.g. `root → subA → BOLT` 与 `root → subB → BOLT` 都要算）。把 `parent_item_id` 纳入 key 是保证跨父件不会被错误合并。

子件解析由既有 `node_map` + `_find_existing(item_number)` 搞定：

- `_find_existing` 在 `item_number` 上做查询（先 `item_number`，再 `drawing_no` fallback），因此「同一个 item_number 映射到同一个 Item.id」这个语义在聚合阶段之前就已稳定。
- 到了聚合阶段，`child_item_id` 已经是 `Item.id`——"resolved child item_id or item_number" 自然被统一成 `child_item_id`。未被解析的 edge（`child_item_id is None`）在 Phase 1 之前就 `skipped_lines += 1` continue。

### 3.2 quantity 相加而不是覆盖

CAD 提取器可能拆分一条逻辑 BOM 行成多条物理 edge（e.g. 同一子件不同实例），相加得到的是该子件在该父件下的总消耗。覆盖会丢信息。

### 3.3 find_num 保留首个非空；refdes 跨 edge 合并 + 去重 + 稳定排序

两个字段采取**不同**策略（本轮 remediation 从单一「首个非空」改为二分策略）：

- **`find_num`**：CAD 提取重复行通常表示同一物理 BOM 行被拆成多条 edge，各条 `find_num` 应当相同；即便不同，也应保留**首个非空**（原子值语义，下游工程制图/position 标注不接受合并字符串）。
- **`refdes`**：PLM 惯例下 `refdes` 是一个**reference designator 集合**（如 `R1,R2,R3`），跨 edge 累积合并是自然的语义。本轮采用：
  - Phase 1：`_refdes_tokens` 按 `,` 或 list/tuple/set 拆分成 token 列表，`None` / 空串被滤掉，累积到 aggregator 的 `set`
  - Phase 2：`_join_refdes_tokens` 做 lexicographic 稳定排序 + 去重 + comma join
  - 例：输入 `"R3"`、`"R1,R2"`、`"R1"`、`None` → 输出 `"R1,R2,R3"`
  - 单 edge 输入 `"R3,R1,R2,R1"` 同样会被排序去重 → `"R1,R2,R3"`

**关于排序稳定性**：采用 Python `sorted(set(...))` 的 lexicographic 排序——对 `R1 / R2 / R3` 直观；对 `R1 / R2 / R10` 会得到 `R1,R10,R2`（lexicographic 下 `R10 < R2`），这是 refdes tokens 作纯字符串排序的已知行为。natural sort 要求由下一增量独立升级，本 PR 不做。

### 3.4 uom 大写归一

PLM 约定 UOM 用大写（`EA` / `KG` / `MM`）。现状 `_normalize_text` 只 strip 不 upper，导致 `"mm"` / `"MM"` 变成两行。本次统一 `.upper()`：

- 聚合 key 用归一后的 uom
- 存入 `meta_bom_relationships.uom` 的也是归一后的 uom（通过 `add_child(uom=...)`）
- 默认值保持 `"EA"`（跟既有代码一致）

**已知副作用**：之前写 `uom="mm"` 进去的调用方，现在会看到存成 `"MM"`。调用方如果有大小写敏感的报表或比对，需要同步更新——本 PR 的 scope 不包含下游调用方的 audit。

### 3.5 结果 schema 的 `dedup_aggregated` 字段

- 新增 key，**不**移除既有 key（`ok / created_items / existing_items / created_lines / skipped_lines / errors`）——前向兼容
- 值含义：被合并的行数，即 `sum(merged_count - 1 for each key)`
  - 示例：3 条 edge 聚成 1 行 → `dedup_aggregated = 2`
  - 示例：2 条 edge 聚成 1 行 + 1 条独立 → `dedup_aggregated = 1`
  - 示例：无重复 → `dedup_aggregated = 0`
- **边界**：`empty_bom` 短路分支（line 135-144）**不**带 `dedup_aggregated`，因为没走 commit 阶段。测试 `test_import_bom_empty_payload_still_returns_consistent_schema` 明确 pin 这个行为，避免未来误被当 bug 修。

## 4. 验证

### 4.1 新增 focused 测试

`src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py`，19 个 test case：

**`_normalize_uom` unit tests（3）**：

- `test_normalize_uom_empty_uses_default` — `None` / `""` / `"   "` 均返回 `"EA"`
- `test_normalize_uom_strips_and_uppercases` — `"mm"` / `" mm "` / `"MM"` → `"MM"`；`" Each "` → `"EACH"`
- `test_normalize_uom_custom_default` — 自定义 default 生效

**`_refdes_tokens` / `_join_refdes_tokens` unit tests（4）**：

- `test_refdes_tokens_none_and_empty` — `None` / `""` / `"   "` → `[]`
- `test_refdes_tokens_from_comma_separated_string` — `"R1,R2,R3"` / `" R1 , R2 , R3 "` / `"R1,,R2,"` 正确拆分 strip
- `test_refdes_tokens_from_list_preserves_input_order` — list/tuple 输入保留顺序，空串与 `None` 被滤除
- `test_join_refdes_tokens_sorts_and_deduplicates` — 排序 + 去重；空输入返回 `None`

**聚合行为 integration tests（11）**：

- `test_import_bom_aggregates_duplicate_edges_same_uom` — 2 dup + 1 独立 → 2 add_child 调用，`dedup_aggregated=1`，summed qty=5
- `test_import_bom_normalizes_uom_case_and_whitespace` — `"mm"`/`" MM "`/`"mM"` 聚合为 1，最终 uom=`"MM"`，qty=10
- `test_import_bom_missing_uom_defaults_to_EA_and_merges_with_explicit_EA` — 缺失/空/显式 `"EA"` 聚合
- `test_import_bom_preserves_first_non_empty_find_num` — None → "10" → "20" 保留 `"10"`（**find_num only**，和 refdes 策略明确分开）
- `test_import_bom_merges_refdes_tokens_across_duplicates_deduped_and_sorted` — `"R3"` + `"R1,R2"` + `"R1"` + `None` → `"R1,R2,R3"`
- `test_import_bom_sorts_single_edge_comma_separated_refdes` — 单 edge `"R3,R1,R2,R1"` → `"R1,R2,R3"`
- `test_import_bom_refdes_all_empty_yields_none` — 所有 edge refdes 为 `None`/`""` → `refdes=None`
- `test_import_bom_no_duplicates_passthrough` — 无 dup，`dedup_aggregated=0`
- `test_import_bom_multi_parent_same_child_is_not_cross_parent_aggregated` — 同子件不同父件 → 不聚合
- `test_import_bom_result_schema_always_includes_dedup_aggregated` — 默认 key 存在
- `test_import_bom_empty_payload_still_returns_consistent_schema` — `empty_bom` 短路分支行为 pin 住

**Real-session integration test（1）**：

- `test_import_bom_real_session_different_uom_creates_two_bom_lines` — **关键补强**：
  - 使用 `tmp_path` + `create_engine(sqlite:///...)` + `Base.metadata.create_all()` 搭建真实 in-memory session
  - 调 `import_all_models()` 保证 FK 解析完整
  - 真实 `BOMService.add_child` 承接两条相同 (parent, child) 不同 uom 的聚合后行
  - 当前断言：`dedup_aggregated=0`（Phase 1 正确保留 uom 独立）+ `created_lines=2` + `skipped_lines=0` + `errors=[]`
  - 原始交付明确记录过当时的 scope 边界：`BOMService.get_bom_line_by_parent_child` 只按 `source_id + related_id` 查唯一。该边界已由 `DEV_AND_VERIFICATION_BOM_UOM_AWARE_DUPLICATE_GUARD_20260421.md` 收敛，现在同 `(parent, child)` 不同 `uom` 可作为两条 BOM line 共存

### 4.2 命令与结果

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py
```

结果：`19 passed in 0.44s`（含 1 个 real-session SQLite test）

### 4.3 回归（确认 dedup 改动不影响相邻主干线）

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_bom_import_dedup_aggregation.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_suspended_write_paths.py \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：`49 passed in 0.52s`

### 4.4 Compile 检查

```bash
.venv/bin/python -m py_compile src/yuantus/meta_engine/services/cad_bom_import_service.py
```

结果：通过。

## 5. 兼容性

### 5.1 Result dict 前向兼容

既有 caller（搜过 repo `import_bom` 调用点）只读 `ok / created_lines / skipped_lines / errors` 等既有 key；新增 `dedup_aggregated` 是可选观察 key，旧代码不受影响。

### 5.2 duplicate edge 之前的行为

之前：第二次 `add_child` 遇到已存在的 (parent, child) 对会抛 `ValueError("BOM relationship already exists: ...")`，被 `except Exception` 吞掉 → `skipped_lines += 1` + errors 追加。

现在：同一 (parent, child, uom) 重复直接在 Phase 1 聚合 → 只有 1 次 `add_child`，不再触发「already exists」错误路径。

**影响**：

- 在 CAD BOM 导入中，「看似重复」的 edge 不再造成 `skipped_lines` 虚高
- `errors` 里不再出现 "BOM relationship already exists" 的条目（前提是 edges 内部重复；跨 import 批次的重复仍然会 raise，因为那时第一次 import 已经入库）

### 5.2a 不同 uom 但同 (parent, child) 的行为（已收敛）

原始 real-session 测试明确了：同一 `(parent, child)` 对，两条 edge 分别 `uom="EA"` / `uom="MM"`，**Phase 1 不会聚合**（uom 是 key 的一部分），但当时 **Phase 2 的第二次 `add_child` 会被 `BOMService.get_bom_line_by_parent_child` 守卫拦截**，因为该守卫只按 `source_id + related_id` 判唯一、**不**考虑 uom。

该 scope 边界已由 `DEV_AND_VERIFICATION_BOM_UOM_AWARE_DUPLICATE_GUARD_20260421.md` 收敛。当前结果：

- `dedup_aggregated = 0`（不是 aggregation 问题）
- `created_lines = 2`
- `skipped_lines = 0`
- `errors = []`

删除路径也相应加了可选 `uom` discriminator：当同 `(parent, child)` 有多条 UOM-specific line 且未指定 `uom` 时，service 会明确报 ambiguous，避免误删第一条。

### 5.3 uom 存储归一

之前 `uom="mm"` 会直接入库。现在 `uom="MM"`。调用方如果有大小写敏感的 BOM 报表，会观察到大写化。这是**有意的归一**，不是回归——但需要在 PR 描述里明确告知。

## 6. 非目标

本 PR 明确不做：

- scheduler / scheduler consumer / activation smoke（A1/A2 另说）
- CAD backend profile 扩展（`plm_automated_convertion` 对标等）
- 142 shared-dev 任何动作
- UI / workbench / plm_workspace 改动
- 跨 import 批次的聚合（只在单次 commit 内聚合）
- schema migration / 新 column
- 多语言 / i18n / 产品描述多语言 helper（§一.6 的另外一半，独立增量）
- **`BOMService.add_child` / `get_bom_line_by_parent_child` 签名变更 · uom 纳入唯一键**——必然的后续增量，但需要独立审阅（索引迁移、where-used 语义、报表影响），不混进本 PR
- `_normalize_refdes` 函数本体不动（保留给非聚合 caller）；本 PR 用独立的 `_refdes_tokens` + `_join_refdes_tokens` 做跨 edge 合并，两套 helper 互不 import

## 7. 独立审阅清单

| # | 检查点 |
|---|---|
| 1 | 聚合 key 是否包含 parent_item_id（多父件不应被错误合并） |
| 2 | `_normalize_uom` 是否 upper + strip + 默认 `EA`，未新增除 `.upper()` 以外的语义 |
| 3 | `find_num` 保留**首个非空**策略；**`refdes` 跨 edge 合并 + 去重 + 稳定排序**——两者策略明确分开，不是统一「首个非空」 |
| 4 | `_refdes_tokens` 能正确处理 `None` in list（应过滤，不要 `str(None)="None"` 泄漏成 token） |
| 5 | `_join_refdes_tokens` 同样过滤 `None`；空输入返回 `None` 而不是 `""` |
| 6 | `dedup_aggregated` 值是否等于 `sum(merged_count - 1)`（不是 edge 总数减聚合后行数这种 off-by-one） |
| 7 | 结果 dict 的既有 key 是否都保留，没有被拼写改名 |
| 8 | 第二阶段 add_child 调用顺序是否按 `aggregation_order` 保持首次出现顺序（不是 dict 随机顺序） |
| 9 | 跨 parent 的同子件 edges 是否真的**不**被聚合（test_import_bom_multi_parent_... 覆盖） |
| 10 | `empty_bom` 短路分支是否保持原行为（不误增 `dedup_aggregated`，不影响既有 caller） |
| 11 | **Real-session test 是否真的用 `create_engine(sqlite:///...)` + `Base.metadata.create_all` + `import_all_models()`**，不是 MagicMock 伪装成 real |
| 12 | 同 (parent, child) 不同 uom 的 real-session test 断言顺序正确（`dedup_aggregated=0` + `created_lines=2` + `skipped_lines=0` + `errors=[]`） |
| 13 | `.venv/bin/python -m py_compile` 通过 |
| 14 | 没有 touch scheduler / CAD profile / 142 / UI 相关文件 |
| 15 | `BOMService.add_child` / `get_bom_line_by_parent_child` 签名变化已由后续 UOM-aware duplicate guard 单独交付 |

## 8. 已知边界与 follow-up

- **同 (parent, child) 不同 uom 不能同时存在** 的旧边界已由 `DEV_AND_VERIFICATION_BOM_UOM_AWARE_DUPLICATE_GUARD_20260421.md` 收敛：现在 duplicate guard 纳入 normalized UOM，同父子不同 UOM 可共存
- `find_num` 保留首个非空已是足够策略；若未来需要跨 edge merge（如带 `find_num="10/20/30"` 语义），再独立升级
- `_refdes_tokens` 的 natural sort follow-up 已由 `DEV_AND_VERIFICATION_REFDES_NATURAL_SORT_20260421.md` 收敛：形如 `R10` / `R2` 的混合现在输出 `R1,R2,R10`
- uom 归一只做到 upper + strip，未做同义映射（e.g. `"EACH"` ↔ `"EA"`、`"MMS"` ↔ `"MM"`）——PLM 里 UOM 字典应该由租户级配置而非硬编码
- 跨 import 批次的重复检测仍然依赖 `BOMService.add_child` 的「relationship already exists」guard，本 PR 不改变那一侧

## 9. Reviewer

本增量由本会话的 Claude 助手单 session 内完成。执行分两轮：

### Round 1（初版）

1. 真实代码勘探：读 `cad_bom_import_service.py` 296 行全文 + `bom_service.add_child` 签名 + 现有 `_normalize_*` helpers
2. 核对 repo 内无既有 `test_cad_bom_import_*` 测试（greenfield 测试文件）
3. 实现 `_normalize_uom` + 两阶段聚合 commit（refdes 用「保留首个非空」策略）
4. 补 12 个测试（3 个 uom 单元 + 9 个 integration，其中 1 个 mock-only 的 different-uom 测试）
5. 跑 focused suite 12 passed + 回归 42 passed + py_compile 通过
6. 写本 MD 的初版

### Round 2（remediation，本次）

根据用户指出的两个问题补强：

1. **refdes 策略从「首个非空」改为「跨 edge 合并 + 去重 + 稳定排序」**：
   - 新增 `_refdes_tokens` + `_join_refdes_tokens` 两个 helper
   - 修 None-in-list 的 `str(None)="None"` token 泄漏 bug
   - Phase 1 累积到 `set`，Phase 2 `_join_refdes_tokens` 输出
   - 补 4 个 helper 单元测试 + 3 个聚合行为测试（合并、单 edge sort、全空→None）
   - 删掉单一「首个非空」的组合测试
2. **替换 mock-only 的 different-uom 测试为 real-session**：
   - 删 `test_import_bom_different_uom_stays_separate`（MagicMock 掩盖了 BOMService duplicate guard 的真实行为）
   - 当时新增 `test_import_bom_real_session_different_uom_second_row_is_skipped_by_bom_guard` 用 `tmp_path` + `create_engine("sqlite:///...")` + `Base.metadata.create_all(engine)` + `import_all_models()` 跑真实 in-memory session
   - 该历史测试 pin 住「同 (parent, child) 不同 uom 的第二行会被 `BOMService.get_bom_line_by_parent_child` 拦截」这一 scope 边界；该边界后续已由 UOM-aware duplicate guard 收敛，测试现名为 `test_import_bom_real_session_different_uom_creates_two_bom_lines`

最终 focused 19 passed + 回归 49 passed + py_compile 通过。

原始 PR scope 严守用户边界：只改 `CadBomImportService`、测试、本 MD、索引；不碰 scheduler / CAD profile / 142 / UI / `BOMService` 签名。后续 `BOMService` 签名变化已在 UOM-aware duplicate guard 增量中单独交付和验证。
