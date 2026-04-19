# DEV / Verification - Shared-dev Bootstrap Env Helper

日期：2026-04-19

## 目标

继续沿 shared-dev bootstrap 线降低执行摩擦，但不再改业务逻辑。

这次只解决一个现实问题：

- “真实 shared-dev 凭证还没出来” 其实只是因为第一次 bootstrap 时还没人定那两个密码。

因此本轮新增一个小 helper，让操作者：

1. 一次命令生成两份 env
2. 自动拿到随机 admin/viewer 密码
3. 不需要再手工想密码，也不需要自己拼 observation env

## 新增内容

### 1. `scripts/generate_p2_shared_dev_bootstrap_env.sh`

功能：

- 生成 server-side bootstrap env
- 生成 operator-side observation env
- 未提供密码时自动生成随机密码
- 对两份输出文件统一 `chmod 600`

默认输出：

- `$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env`
- `$HOME/.config/yuantus/p2-shared-dev.env`

默认参数：

- `tenant-1`
- `org-1`
- `admin`
- `ops-viewer`
- `BASE_URL=https://<shared-dev-host>`

### 2. `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md`

增加第 0 步：

- 优先先跑 helper 生成 env

并把服务器侧 bootstrap env 的准备改成：

- 优先从 `$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env` 复制

### 3. `scripts/print_p2_shared_dev_bootstrap_commands.sh`

更新为：

- 先打印 helper 用法
- 再打印 server-side bootstrap
- 再打印 operator-side observation

## 为什么值得单独做

此前虽然已经有：

- bootstrap 能力
- bootstrap handoff

但操作者还是要自己完成两件最容易出错的事：

1. 决定两个真实密码
2. 同步改两份 env

这个 helper 把这两步都收掉了。

## 验证

本轮是 docs/tooling 级验证。

实际执行：

```bash
bash scripts/generate_p2_shared_dev_bootstrap_env.sh \
  --base-url "https://shared-dev.example.internal" \
  --bootstrap-out /tmp/yuantus-bootstrap-env-helper/bootstrap.env \
  --observation-out /tmp/yuantus-bootstrap-env-helper/p2.env

sh -n scripts/generate_p2_shared_dev_bootstrap_env.sh
bash scripts/print_p2_shared_dev_bootstrap_commands.sh
```

检查点：

- 两份 env 文件都成功生成
- 两份文件权限都是 `600`
- bootstrap env 包含：
  - admin/viewer 两个密码
  - `p2-observation` dataset mode
- observation env 包含：
  - `BASE_URL`
  - `admin` 凭证
  - tenant/org
- 命令打印脚本已经改为优先走 helper 路径

## 边界

- 该 helper **不会**自动把 bootstrap env 推到服务器
- 该 helper **不会**直接执行 docker compose
- 该 helper 只负责把“真实 shared-dev 凭证”初始化出来，并写成安全权限的本地文件

## 结论

这条 follow-up 做完后，操作者要完成真实 shared-dev 初始化，只需要：

1. 本地执行 helper
2. 把 bootstrap env 复制到服务器
3. 服务器上跑 bootstrap
4. 本地直接跑 precheck + wrapper

也就是说，真实 shared-dev 凭证现在可以在 1 分钟内生成出来，不再需要手工构造。
