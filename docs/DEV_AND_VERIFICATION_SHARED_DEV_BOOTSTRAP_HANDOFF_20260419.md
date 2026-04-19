# DEV / Verification - Shared-dev Bootstrap Handoff

日期：2026-04-19

## 目标

在 `#255/#256` 已经把 shared-dev bootstrap 能力和 P2 observation fixture 补齐的前提下，再补一条纯 handoff follow-up：

- 给远端操作者一份可照抄执行的 bootstrap runbook
- 给本地操作者一份可直接打印的命令模板
- 明确区分：
  - 服务器侧 bootstrap env
  - 操作机侧 observation env

这样后续执行不需要再回到 PR 对话里拼步骤。

## 新增内容

1. `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md`
   - 固定 shared-dev 初始化顺序
   - 包含：
     - bootstrap env 准备
     - `docker compose --profile bootstrap run --rm bootstrap`
     - 常驻服务启动
     - health check
     - 本地 `p2-shared-dev.env`
     - precheck / wrapper 执行
   - 明确了预期 observation 指标：
     - baseline `1 / 2 / 0`
     - after escalate `1 / 3 / 1`
     - tri-state `401 / 403 / 200`

2. `scripts/print_p2_shared_dev_bootstrap_commands.sh`
   - 非交互打印：
     - 服务器侧 bootstrap 命令
     - 操作机侧 env 落地命令
     - observation 执行命令
   - 与已有 `print_p2_shared_dev_observation_commands.sh` 形成前后衔接

## 为什么单独开这条 follow-up

`#255/#256` 解决的是“能力是否存在、是否验证通过”。  
这条 follow-up 解决的是“真实操作者怎么最快执行”。

如果不把这部分单独固化，shared-dev 初始化仍然依赖：

- 阅读多个 PR
- 手工拼 env
- 手工摘命令

这对值班/运维执行不友好。

## 验证

本轮验证是 handoff/script 级别，不是再次跑业务 e2e。

实际执行：

- `bash scripts/print_p2_shared_dev_bootstrap_commands.sh`
- 手工审阅 `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md`
- 对照既有：
  - `README.md`
  - `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
  - `scripts/print_p2_shared_dev_observation_commands.sh`

确认：

- 没有把 bootstrap 和 observation env 混在一起
- 没有把长期 secret 写进仓库
- 命令顺序与 `#255/#256` 的能力边界一致
- 与已有 observation handoff 是衔接关系，不是重复造轮子

## 结论

这条 follow-up 是 docs/script-only，但能显著降低 shared-dev 初始化的操作成本。  
合并后，执行人只需要：

1. 在服务器上设置两个 bootstrap 密码
2. 跑 bootstrap
3. 在本机写 `p2-shared-dev.env`
4. 跑 precheck + wrapper

就能把 shared-dev observation 真正落地起来。
