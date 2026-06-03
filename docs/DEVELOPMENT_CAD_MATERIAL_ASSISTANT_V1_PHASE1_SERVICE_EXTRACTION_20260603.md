# CAD 物料助手 v1 — Phase 1 任务书：共享 service 抽取 + CI 对账

- Date: 2026-06-03
- Status: Task (doc-only; 实现需单独开工授权)
- Parent plan: `docs/DEVELOPMENT_CAD_MATERIAL_ASSISTANT_V1_PLAN_20260603.md`
- Phase: 1 / N（仅本阶段；assistant、相似度、Helper/AutoCAD 见后续 Phase）

## 1. 目标

把 `yuantus-cad-material-sync` 插件里的 **compose / validate / match / create 叶子原语**抽到可复用 service，**行为逐字节不变**，并修正 CI 对账，使现有 material-sync 回归真正在 CI 跑绿。这是纯内部重构，给后续 assistant 层提供可复用原语。

## 2. 非目标（本阶段明确不做）

- 不新增 `assistant/resolve`、`assistant/create` 或任何新路由。
- 不做字段相似评分、dedup_vision 接入。
- 不动 Helper Bridge、AutoCAD 客户端。
- 不改任何响应字段、不加行为开关/feature flag。
- 不搬 `/sync/inbound` 的状态机（见 §3.2）。
- 不动 `load_profiles` 及其 governance/rollout/versioning/config 链（见 §3.1）。

## 3. 抽取方案（4 条硬约束）

### 3.1 切口在"已解析 profile"层

- 新 service 函数只吃 `(db, profile_dict, values, user)`，**不**做 profile 解析。
- `load_profiles`（`plugins/yuantus-cad-material-sync/main.py:1102`）及其 governance/rollout/versioning/config helper（约 :516–1002）**留在插件原处**——那是真正缠绕的部分，本阶段不碰。
- 路由仍在插件里先 `load_profiles()` → `_get_profile()` 得到 `profile` dict，再把 dict 交给 service。

### 3.2 只抽叶子原语，inbound 状态机留在 handler

本阶段搬迁的函数（当前行号）：

| 函数 | 当前位置 |
|---|---|
| `compose_profile(profile, values)` | `main.py:1635` |
| `validate_profile_values(...)` | `main.py:1332` |
| `_match_strategies(profile)` | `main.py:1839` |
| `_find_matching_items(db, profile, values)` | `main.py:1881` |
| `_apply_item_create(db, profile, properties, user)` | `main.py:2013` |
| `_apply_item_update(db, item, updates, user)` | `main.py:1994` |

- `/sync/inbound`（`main.py:2388`）里的 `ambiguous_match / conflict / not_found / create / update` 分支编排**内联保留在路由处理器，原样不动**。assistant（Phase 2）届时用这些叶子自行拼编排。

### 3.3 `main.py` 必须 re-export 被搬走的函数（最关键）

- 回归测试 `test_plugin_cad_material_sync.py` 用 `importlib.util` 从**文件路径**加载插件，再以 `module.compose_profile(...)` 等**模块属性**直接调用（45 个用例）。
- 函数体搬进 service 后，`main.py` 顶部必须显式 re-import，使这些名字仍是插件模块属性：
  ```python
  from yuantus.meta_engine.services.cad_material_sync_service import (
      compose_profile,
      validate_profile_values,
      _match_strategies,
      _find_matching_items,
      _apply_item_create,
      _apply_item_update,
  )
  ```
- 这样路由（按裸名调用）与测试（按 `module.X` 调用）两边同时绿。**漏掉 re-export = 一片红回归。**
- service 模块落点：`src/yuantus/meta_engine/services/cad_material_sync_service.py`（与 `search_service.py`、`equivalent_service.py` 同目录）。

### 3.4 CI 顺序：先绿基线，再抽取（拆两个 commit）

- **Commit A（CI 对账）**：把 `src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py` 加进 `.github/workflows/ci.yml` 的 `plugin-tests` 显式清单（当前 :582–583 只跑 `test_plugin_pack_and_go.py` + `test_plugin_bom_compare.py`）。**在未改动业务代码上跑绿**——这是基线。
- **Commit B（service 抽取）**：执行 §3.1–3.3 的搬迁 + re-export。
- 拆开的理由：若先抽取再加 CI，变红时无法区分"抽取引入回归"还是"测试本来没跑过"。

## 4. 验收清单

- `test_plugin_cad_material_sync.py` 全 **45** 用例绿；该文件已在 `ci.yml` `plugin-tests` 清单内。
- 抽取前后 `/compose`、`/validate`、`/diff/preview`、`/sync/inbound`、`/sync/outbound` 响应**逐字节一致**（45 用例 + 路由级用例即 oracle）。
- 护栏（diff 自检）：无新增路由、无行为开关、无响应字段变化——`git diff` 中插件路由签名与 response model 零改动。
- service 函数签名只接受 `(db, profile_dict, values, ...)`，不含 profile 解析逻辑。
- `main.py` 对六个函数均有 re-export；`python3 -c "import importlib; ...; assert hasattr(module, 'compose_profile')"` 类断言通过。
- 边界确认：`test_cad_material_sync_*solidworks*` 等是**契约/文档级**测试，不纳入本阶段功能桩范围（如需纳入其它*功能型* plugin 测试由负责人单独决定，勿混入契约测试扩大范围）。

## 5. 验证命令

```bash
# 功能桩（抽取前后均须全绿）
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q

# re-export 自检（搬迁后）
PYTHONPATH=src python3 - <<'PY'
import importlib.util, pathlib
p = pathlib.Path("plugins/yuantus-cad-material-sync/main.py")
spec = importlib.util.spec_from_file_location("cad_material_sync_main", p)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for name in ("compose_profile","validate_profile_values","_match_strategies",
             "_find_matching_items","_apply_item_create","_apply_item_update"):
    assert hasattr(m, name), f"missing re-export: {name}"
print("re-export OK")
PY
```

## 6. 风险与陷阱

- **re-export 遗漏**（§3.3）：最高频翻车点，由 §5 自检兜底。
- **CI 假绿**：测试不进 `ci.yml` 清单则等于没跑（仓库已知坑）——Commit A 先行解决。
- **scope 蔓延**：把 inbound 状态机或 `load_profiles` 一起搬，会放大 blast radius 并难判回归——§3.1/§3.2 已划死。
- **lazy import 副作用**：`_apply_item_create` 内部 lazy import `AMLEngine`（`main.py:2019-2020`），搬迁后保持函数内 import 即可，勿提到模块顶层（避免引入循环依赖）。

## 7. 出口 / 交接到 Phase 2

Phase 1 完成后，Phase 2（assistant resolve/create + 字段相似评分）可直接复用 `cad_material_sync_service` 的叶子原语自行编排，无需再触碰插件路由。Phase 2 需单独开工授权。
