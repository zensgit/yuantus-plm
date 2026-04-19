# DEV & VERIFICATION - Shared-dev First-run Checklist - 2026-04-19

## Development

### Scope

在 `#255-#259` 已经把 bootstrap、fixture、handoff、env helper、env validator 补齐之后，最后还缺一个单入口：

- 操作者不应再在 README、bootstrap handoff、observation handoff、print scripts 之间来回跳
- 第一次 shared-dev 执行应该有一份固定顺序的 checklist

所以这轮只补：

- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- `scripts/print_p2_shared_dev_first_run_commands.sh`

并把 README / bootstrap handoff 指向这个单页入口。

### Files

新增：

- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- `scripts/print_p2_shared_dev_first_run_commands.sh`
- `docs/DEV_AND_VERIFICATION_SHARED_DEV_FIRST_RUN_CHECKLIST_20260419.md`

更新：

- `README.md`
- `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `scripts/print_p2_shared_dev_observation_commands.sh`

### Behavior

新的 first-run checklist 把首次 shared-dev 执行固定成 10 步：

1. 本地生成 bootstrap/observation env
2. 本地 validate env
3. 复制 bootstrap env 到服务器
4. 服务器执行 bootstrap
5. 启动常驻服务
6. 做 health check
7. 操作机再次 validate observation env
8. 跑 precheck
9. precheck 绿后再跑 wrapper
10. 回传核心产物

同时把“fresh shared-dev 首次执行”和“已有凭证后的 rerun”明确拆开：

- first-run：
  - `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
  - `scripts/print_p2_shared_dev_first_run_commands.sh`
- rerun / existing credentials：
  - `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
  - `scripts/print_p2_shared_dev_observation_commands.sh`

## Verification

### 1. Syntax check

```bash
bash -n scripts/print_p2_shared_dev_first_run_commands.sh
```

结果：

- 通过

### 2. Printed command sheet

执行：

```bash
bash scripts/print_p2_shared_dev_first_run_commands.sh | sed -n '1,200p'
```

确认：

- 包含 bootstrap 前 validate
- 包含 server-side bootstrap + health
- 包含 observation-side validate + precheck + wrapper
- 顺序与当前 helper-first / validator-first 流程一致
- 明确是 fresh shared-dev 的 first-run 入口

### 3. Doc linkage

确认：

- `README.md` 已指向：
  - `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
  - `scripts/print_p2_shared_dev_first_run_commands.sh`
- `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md` 已指向同一单页入口
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md` 已明确标成 existing-credentials rerun 入口
- `scripts/print_p2_shared_dev_observation_commands.sh` 已明确提示 first-run 不应从该脚本开始

## Result

这轮之后，fresh shared-dev 的第一次执行不再需要在多份 handoff 之间人工拼接顺序。  
操作者可以直接：

```bash
bash scripts/print_p2_shared_dev_first_run_commands.sh
```

然后按固定顺序执行。
