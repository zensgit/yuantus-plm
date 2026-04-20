# DEV / Verification - Shared-dev 142 Readonly Guard Post-merge Validation

日期：2026-04-20
仓库基线：`912cf63`（`feat(ops): add shared-dev 142 readonly guard workflow (#289)`）

## 目标

在 `shared-dev-142-readonly-guard` 合并进 `main` 后，做第一次真实 GitHub Actions dispatch，确认：

1. 新 workflow 已被 default branch 正常注册
2. workflow 能成功调用既有 `p2-observation-regression`
3. artifact 下载、readonly compare、readonly eval 会在真实 runner 上执行
4. 最终失败/成功信号能准确反映 shared-dev `142` 当前状态

## 本轮执行

### 1. 合并 guard workflow PR

- PR: `#289`
- merge commit: `912cf630e66d230a8442a208c24ecffcbd5474bf`

### 2. 在 default branch 上手动触发 guard

执行：

```bash
gh workflow run shared-dev-142-readonly-guard.yml -R zensgit/yuantus-plm
```

真实 outer run：

- workflow: `shared-dev-142-readonly-guard`
- run id: `24660213786`
- URL: `https://github.com/zensgit/yuantus-plm/actions/runs/24660213786`

guard 内部触发的 observation workflow：

- workflow: `p2-observation-regression`
- run id: `24660219974`

### 3. 采集失败日志与 artifact

执行：

```bash
gh run view 24660213786 -R zensgit/yuantus-plm --log-failed
gh run download 24660213786 -R zensgit/yuantus-plm -D <tmpdir>
```

下载到的关键文件：

- `shared-dev-142-readonly-guard/24660213786/WORKFLOW_READONLY_CHECK.md`
- `shared-dev-142-readonly-guard/24660213786/WORKFLOW_READONLY_DIFF.md`
- `shared-dev-142-readonly-guard/24660213786/WORKFLOW_READONLY_EVAL.md`
- `shared-dev-142-readonly-guard/24660213786/workflow-probe/WORKFLOW_DISPATCH_RESULT.md`
- `shared-dev-142-readonly-guard/24660213786/workflow-probe/artifact/*`

## 结果

### 1. workflow 本身已经真实打通

`shared-dev-142-readonly-guard` 在 GitHub runner 上已经完成了完整链路：

1. 从 tracked baseline 恢复 canonical readonly baseline
2. dispatch `p2-observation-regression`
3. 等待 workflow 完成
4. 下载 artifact
5. 生成 readonly diff / eval / check

这说明：

- `#289` 的核心目标已经实现
- 之前“新 workflow 合并前不能 dispatch”的边界，在合并后已消失

### 2. guard 失败，但失败原因是数据漂移，不是实现故障

outer run 最终是 `FAIL`，但失败点来自 readonly evaluation：

- `WORKFLOW_READONLY_CHECK.md`
  - `status: failure`
  - `reason: readonly evaluation failed`
- `WORKFLOW_READONLY_EVAL.md`
  - `verdict: FAIL`
  - `checks: 16/20 passed`

当前 shared-dev `142` 相对 frozen readonly baseline 的实际漂移：

- `pending_count`: `2 -> 1`
- `overdue_count`: `3 -> 4`
- `escalated_count`: `1 -> 1`
- `total_anomalies`: `2 -> 3`
- `overdue_not_escalated`: `1 -> 2`

items/export 行数仍保持一致：

- `items_count`: `5 -> 5`
- `export_json_count`: `5 -> 5`
- `export_csv_rows`: `5 -> 5`

这说明：

- workflow guard 没坏
- shared-dev `142` 当前观测面已经偏离 `20260419` 的 frozen readonly baseline

### 3. 嵌套 observation workflow 是成功的

被 guard 调起的 `p2-observation-regression` run `24660219974` 完整通过：

- `Validate auth configuration`
- `Run P2 observation regression`
- `Write observation summary to job summary`
- `Upload P2 observation regression evidence`

所以当前 blocker 不是：

- GitHub Actions secret
- dispatch 权限
- artifact 下载
- workflow wiring

而是：

- readonly baseline 稳定性本身已经被 guard 识别为漂移

### 4. 非阻塞注记

本轮仍有一条非阻塞 annotation：

- `actions/upload-artifact@v4` 的 Node.js 20 deprecation 提示

这不是本轮失败根因。

## 验证

执行：

```bash
gh workflow run shared-dev-142-readonly-guard.yml -R zensgit/yuantus-plm
gh run view 24660213786 -R zensgit/yuantus-plm --log-failed
gh run download 24660213786 -R zensgit/yuantus-plm -D <tmpdir>
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

结果：

- GitHub workflow dispatch：成功
- nested observation workflow：成功
- readonly guard verdict：`FAIL`
- doc index tests：通过

## 结论

`shared-dev-142-readonly-guard` 已经正式进入“可真实守护”状态。

本轮最重要的结论不是“workflow 还要修”，而是：

1. workflow guard 已真实跑通
2. shared-dev `142` 当前观测面相对 frozen baseline 已发生漂移
3. 下一步应在两条路径里二选一：
   - 调查 shared-dev `142` 为什么发生 readonly drift
   - 或按既有流程做一次新的 readonly refreeze / baseline refresh
