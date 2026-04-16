# PLM Main Chain Convergence — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-15
**Status:** ✅ 241 passed, 0 failed, 0 regressions

---

## 1. One-Line Goal

> 先收敛一条可运营的PLM主链，再补Odoo风格的小addon能力

---

## 2. 收敛前的问题

| 问题 | 具体表现 |
|---|---|
| CAD checkin 是 stub | `subprocess.run(["true"])` + `upload_file(b"", ".viewable")` — 没有真实转换 |
| 双写转换 job | file_router 写 `cad_conversion_jobs`，checkin 写 `meta_conversion_jobs` — 两套表、两个 worker |
| Derived files 不绑定版本 | handler 执行完把 preview/geometry path 写到 FileContainer 字段，但 VersionFile 里没有对应记录 |
| 读模型看不到 derived files | `product_service` / `query_service` 读 ItemFile，VersionFile 的 preview/geometry 没映射过来 |
| 文件锁累积 | 重新 checkin 产生新 native_file，旧的 preview VersionFile 不删除，一个版本可能累积多条同 role 记录 |
| File-level checkout 缺失 | 只有 version-level 锁，无法按文件粒度锁 |
| `result_file_id` 不反映状态 | 总是返回 None，无法区分 completed job 的输出 |
| Process 端点统计错 | `run_once()` 返回 True 就算成功，实际可能已 fail_job |

---

## 3. 阶段化交付

### P1-4: CAD Checkin Transaction Chain

**文件**: `services/checkin_service.py`

```python
# BEFORE (stub)
subprocess.run(["true"], check=False)
viewable = file_service.upload_file(b"", f"{Path(filename).stem}.viewable")

# AFTER (real pipeline)
preview_job  = job_service.create_job("cad_preview",  payload, max_attempts=3, dedupe=True)
geometry_job = job_service.create_job("cad_geometry", payload|{"target_format":"glTF"}, ...)
```

Payload 携带 `version_id`，worker 后处理用于 VersionFile 绑定。

### P1-5: Handler → VersionFile Binding Wrappers

**文件**: `tasks/cad_pipeline_tasks.py`, `cli.py`

不改已有 handler 的 8+ 条 return 路径，而是加薄包装器：

```python
def _enrich_with_derived_files(result, payload, file_role):
    if result.get("ok") and payload.get("version_id"):
        result["derived_files"] = [{
            "file_id": result["file_id"],
            "file_role": file_role,
            "version_id": payload["version_id"],
        }]
    return result

def cad_preview_with_binding(payload, session):
    return _enrich_with_derived_files(cad_preview(payload, session), payload, "preview")

def cad_geometry_with_binding(payload, session):
    return _enrich_with_derived_files(cad_geometry(payload, session), payload, "geometry")
```

`cli.py` 改注册 `_with_binding` 变体替代原始 handler。

### P1-4.1: Conversion Job Queue Convergence

**文件**: `web/file_router.py`

6 个 conversion 端点从 `cad_conversion_jobs` 切到 `meta_conversion_jobs`：

| 端点 | 之前 | 之后 |
|---|---|---|
| `POST /{file_id}/convert` | `CADConverterService.create_conversion_job()` | `JobService.create_job("cad_preview"\|"cad_geometry")` |
| `GET /conversion/{job_id}` | 只查 legacy | canonical 优先，fallback legacy |
| `GET /conversions/pending` | legacy | canonical filter by task_type |
| `POST /conversions/process` | `process_batch()` | deprecated → `JobWorker.run_once()` + 精确统计 |
| 文件上传 preview | `create_conversion_job("png")` | `JobService.create_job("cad_preview")` |
| `POST /process_cad` legacy | `create_conversion_job()` | `JobService.create_job()` |

**Dual-read fallback**: 旧 job id 在兼容期仍可查询。

### P1-4.2: VersionFile → ItemFile Projection

**文件**: `services/job_worker.py`

Worker 绑定 derived files 后，如果 version 是 current version，自动调用 `sync_version_files_to_item(remove_missing=False)` 投影到 ItemFile，确保 `product_service` / `query_service` 读模型能看到 preview/geometry。

### Fix 1: VersionFile dedup by (version_id, file_role)

**文件**: `version/file_service.py` `attach_file()`

重新 checkin 产生新 native_file，旧 preview VersionFile 需按 `(version_id, file_role)` 替换而非累积。`attachment` 角色除外（允许多附件）。

```python
if file_role not in ("attachment",):
    stale = session.query(VersionFile).filter_by(
        version_id=version_id, file_role=file_role
    ).filter(VersionFile.file_id != file_id).all()
    for old_vf in stale:
        session.delete(old_vf)
```

### Fix 2: result_file_id 语义

**文件**: `web/file_router.py` `_meta_job_to_response()`

Completed job 从 `payload["result"]["file_id"]` 取；non-completed 返回 None。

```python
result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
result_file_id = result.get("file_id") if job.status == COMPLETED else None
```

### Fix 3: Process endpoint 统计准确

**文件**: `web/file_router.py` `process_conversion_queue`

不再用 `run_once()`（无法区分成功/失败），改用 `job_service.poll_next_job()` + `worker._execute_job()` + `db.refresh(job)` 检查真实 `job.status`。

```python
for _ in range(batch_size):
    job = js.poll_next_job("http-batch")
    if not job:
        break
    worker._execute_job(job, js)
    db.refresh(job)
    if job.status == COMPLETED:
        results["succeeded"] += 1
    else:
        results["failed"] += 1
```

### File-Level Checkout

**Model**: `version/models.py`

`VersionFile` 新增:
```python
checked_out_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
checked_out_at    = Column(DateTime, nullable=True)
```

**Service**: `version/file_service.py`

- `checkout_file(version_id, file_id, user_id, *, file_role)` — 检查 version released/locked → file lock → 写锁
- `undo_checkout_file()` — 只允许锁持有人释放
- `get_file_lock()` — 查状态
- `assert_file_unlocked()` — 元数据编辑守卫
- `_get_version_file_assoc()` / `find_version_file_assoc()` — 内部工具

**Router**: `web/version_router.py`

| 端点 | 作用 |
|---|---|
| `POST /{version_id}/files/{file_id}/checkout` | 锁定 |
| `POST /{version_id}/files/{file_id}/undo-checkout` | 释放 |
| `GET /{version_id}/files/{file_id}/lock` | 查状态 |
| `DELETE /{version_id}/files/{file_id}` | 增加 `_ensure_version_file_lock_clear` 守卫 |
| `GET /{version_id}/files` | 返回体含 `checked_out_by_id` / `checked_out_at` |

错误码: 409 冲突、404 不存在、400 其他。

### release_all_file_locks on checkin

**文件**: `version/file_service.py` + `version/service.py`

Checkin 意味着"编辑完成"，所有文件锁应一并清理。`VersionService.checkin()` 在释放版本锁后自动调用 `release_all_file_locks(version.id)`。

---

## 4. 端到端主链（收敛后）

```
User → CheckinManager.checkin(item_id, bytes, filename)
  │
  ├─ upload native → FileContainer(is_native_cad=True)
  ├─ JobService.create_job("cad_preview",  payload{file_id, version_id, ...}, dedupe=True)
  ├─ JobService.create_job("cad_geometry", payload|{target_format:"glTF"}, dedupe=True)
  └─ VersionService.checkin()
         ├─ sync native_cad → VersionFile
         ├─ release version lock
         └─ release_all_file_locks()

Worker → JobWorker.run_loop()
  ├─ pick cad_preview job
  ├─ cad_preview_with_binding() → 真实转换 + derived_files 富化
  ├─ post-processor:
  │    ├─ VersionFile.attach_file(version_id, file_id, "preview")  [dedup by role]
  │    └─ if version.is_current: sync_version_files_to_item(remove_missing=False)
  └─ complete_job()

File-level lock (optional granular):
  POST /versions/{ver}/files/{f}/checkout  → checked_out_by_id=user
  POST /versions/{ver}/files/{f}/undo-checkout → clears
  Guards: detach_file / set_primary → assert_file_unlocked()
  Auto-release: VersionService.checkin() → release_all_file_locks()

Conversion queue (single path):
  All entry points → JobService → meta_conversion_jobs
    ├─ CheckinManager.checkin
    ├─ POST /file/{id}/convert
    ├─ File upload preview
    ├─ POST /process_cad (legacy)
    └─ worker CLI processes
  Legacy cad_conversion_jobs: read-only fallback for GET /conversion/{id}
```

---

## 5. 文件改动清单

| 文件 | 改动类型 |
|---|---|
| `src/yuantus/meta_engine/services/checkin_service.py` | stub → job queue |
| `src/yuantus/meta_engine/services/job_worker.py` | derived-file post-processor + ItemFile sync |
| `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py` | `_enrich_with_derived_files` + 2 wrappers |
| `src/yuantus/cli.py` | 注册 `_with_binding` wrappers |
| `src/yuantus/meta_engine/version/file_service.py` | dedup + 4 checkout methods + `release_all_file_locks` |
| `src/yuantus/meta_engine/version/models.py` | `VersionFile.checked_out_by_id/at` |
| `src/yuantus/meta_engine/version/service.py` | `checkin()` 自动释放文件锁 |
| `src/yuantus/meta_engine/web/file_router.py` | 6 端点切 canonical + `_meta_job_to_response` helper |
| `src/yuantus/meta_engine/web/version_router.py` | 3 新端点 + `_ensure_version_file_lock_clear` 守卫 |

---

## 6. 测试覆盖

| 测试文件 | 数量 | 覆盖 |
|---|---|---|
| `test_checkin_manager.py` | 4 | delegation, job enqueue, no subprocess |
| `test_cad_checkin_transaction.py` | 18 | job queue, worker binding, enrich, dedup, lock release |
| `test_version_file_checkout_service.py` | 8 | checkout/undo/lock/assert 各分支 |
| `test_file_conversion_router_job_queue.py` | 12 | response mapping, dual-read, preview formats, stats |
| **PLM convergence 小计** | **42** | |
| **全量 meta_engine/tests/** | **241** | 0 failed, 0 regressions |

---

## 7. 验证命令

```bash
# PLM 收敛子集（快速）
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_service.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  -v

# 期望: 42 passed

# 全量回归
python3 -m pytest src/yuantus/meta_engine/tests/ -q

# 期望: 241 passed, 0 failed
```

---

## 8. 验收标准（逐条对账）

- [x] 新 conversion 请求不再写 `cad_conversion_jobs`
- [x] file_router 的 conversion/status/pending/process 全部走 canonical `meta_conversion_jobs`
- [x] 旧 job id 在兼容期仍可查询（dual-read fallback）
- [x] `CADConverterService` 不再是第二套队列入口（标 legacy）
- [x] Current version 的 ItemFile 能看到 preview/geometry
- [x] `CheckinManager.checkin()` 不再调用 `subprocess.run(["true"])`
- [x] 不会累积同 `(version_id, file_role)` 的多条 VersionFile
- [x] `result_file_id` 对 completed job 返回真实值
- [x] Process 端点统计反映 `job.status`
- [x] File-level checkout service + router 完备
- [x] Version checkin 自动释放所有文件锁
- [x] 没有改 CAD 功能面（不改 CADConverter 的直接转换逻辑）
- [x] 没有删旧 `cad_conversion_jobs` 表（留作 fallback）

---

## 9. 下一步建议（addon 阶段）

| 优先级 | 项 |
|---|---|
| 1 | ECO stage SLA dashboard（可视化停留/超时） |
| 2 | BOM comparison diff view（两版本差异 UI） |
| 3 | Approval workflow templates（可配置审批流） |
| 4 | CAD viewer integration（glTF 在线预览） |
| 5 | Legacy `/ecm` + `cad_conversion_jobs` sunset（确认 zero traffic 后清理） |
