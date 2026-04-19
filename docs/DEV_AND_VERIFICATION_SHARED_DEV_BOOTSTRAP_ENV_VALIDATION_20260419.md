# DEV & VERIFICATION - Shared-dev Bootstrap Env Validation - 2026-04-19

## Development

### Scope

在 shared-dev 第一次初始化前，补一层明确的 env 校验与执行防呆，避免操作员在真实外部依赖前才发现：

- bootstrap env 还保留 `change-me-*`
- observation env 还保留 `<jwt>` / `<dev-host>` 这类占位符
- `TENANT_ID` / `ORG_ID` 缺失
- `run_p2_observation_regression.sh` 宣称支持的筛选条件没有真正透传
- handoff 文档没有强调必须从仓库根目录执行相对路径命令

### Code changes

#### 1. New env validator

新增：

- `scripts/validate_p2_shared_dev_env.sh`

能力：

- 校验 server-side bootstrap env
- 校验 operator-side observation env
- 支持：
  - `--mode bootstrap`
  - `--mode observation`
  - `--mode both`
- 拒绝常见占位符：
  - `<...>`
  - `change-me-*`
- 强制 shared-dev observation env 提供：
  - `BASE_URL`
  - `TENANT_ID`
  - `ORG_ID`
  - `ENVIRONMENT`
- 强制 observation 认证方式满足其一：
  - `TOKEN`
  - `USERNAME + PASSWORD`

#### 2. Wrapper filter forwarding fix

修正：

- `scripts/run_p2_observation_regression.sh`

把 wrapper 声明支持的筛选条件真正透传给 `scripts/verify_p2_dev_observation_startup.sh`：

- `COMPANY_ID`
- `ECO_TYPE`
- `ECO_STATE`
- `DEADLINE_FROM`
- `DEADLINE_TO`

这样 shared-dev 观察回归在带过滤条件执行时，不会出现“看起来跑通，但其实验证了错误切片”的假绿。

#### 3. Handoff consistency

更新：

- `scripts/generate_p2_shared_dev_bootstrap_env.sh`
- `scripts/print_p2_shared_dev_bootstrap_commands.sh`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md`
- `README.md`

统一收口：

- helper-first 为首选路径
- 明确相对路径命令必须从 repo root 执行
- 在 bootstrap / observation 执行前先跑 `validate_p2_shared_dev_env.sh`

## Verification

### 1. Syntax checks

```bash
bash -n scripts/validate_p2_shared_dev_env.sh
bash -n scripts/generate_p2_shared_dev_bootstrap_env.sh
bash -n scripts/print_p2_shared_dev_bootstrap_commands.sh
bash -n scripts/print_p2_shared_dev_observation_commands.sh
bash -n scripts/run_p2_observation_regression.sh
```

结果：

- 全部通过

### 2. Helper -> validator closed loop

执行：

```bash
tmpdir=$(mktemp -d)
bootstrap="$tmpdir/bootstrap.env"
observation="$tmpdir/p2.env"

bash scripts/generate_p2_shared_dev_bootstrap_env.sh \
  --base-url "https://shared-dev.example.internal" \
  --bootstrap-out "$bootstrap" \
  --observation-out "$observation"

bash scripts/validate_p2_shared_dev_env.sh \
  --mode both \
  --bootstrap-env "$bootstrap" \
  --observation-env "$observation"

stat -f '%Lp %N' "$bootstrap" "$observation"
```

结果：

- bootstrap env 通过校验
- observation env 通过校验
- 两个文件权限均为 `600`

### 3. Placeholder rejection

执行：

```bash
tmpdir=$(mktemp -d)
bad="$tmpdir/p2.env"
cat > "$bad" <<'EOF'
BASE_URL="http://<dev-host>"
TOKEN="<jwt>"
TENANT_ID="tenant-1"
ORG_ID="org-1"
ENVIRONMENT="shared-dev"
EOF

bash scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$bad"
```

结果：

- 按预期失败
- 明确拒绝 `BASE_URL="http://<dev-host>"` 这种占位符输入

### 4. Filter forwarding proof

为了避免真实打外部依赖，使用临时 stub 验证 wrapper 实际透传到 `verify_p2_dev_observation_startup.sh` 的环境变量。

验证结果：

- `COMPANY_ID=company-1`
- `ECO_TYPE=eco`
- `ECO_STATE=pending`
- `DEADLINE_FROM=2026-04-01T00:00:00Z`
- `DEADLINE_TO=2026-04-30T23:59:59Z`

说明透传修复已生效。

## Result

这轮之后，shared-dev 第一次执行从“靠人工记忆命令和检查占位符”收成了更稳的路径：

1. helper 生成 env
2. validator 拦住占位符/漏项
3. bootstrap / precheck / regression 再真正打远端

同时 shared-dev 观察回归的筛选参数也不再 silently ignored。
