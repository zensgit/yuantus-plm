# 设计文档：并行支线 P2 Doc-Sync Mirror Health/Auth Compatibility

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：提升 remote site 探活兼容性，支持 mirror 服务路径与 basic/token 鉴权。

## 1. 目标

1. 兼容 mirror 类服务缺省无 `/health` 的场景。
2. 探活支持 `token/basic/none` 三种鉴权模式。
3. 返回探活命中目标与鉴权模式，提升排障可观测性。

## 2. 方案

## 2.1 服务层

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增/扩展：

1. `_normalize_remote_auth_mode(...)`
- 约束 `auth_mode` 为 `token/basic/none`。

2. `_build_remote_probe_auth(...)`
- token：Bearer 头；
- basic：支持 metadata username/password 与 secret 回退解析（`user:pass`）。

3. `_build_remote_probe_targets(...)`
- 按优先级探测：
  - `metadata.health_path/probe_path`
  - `/health`
  - `/healthz`
  - `/document_is_there/0`（mirror 兼容）

4. `probe_remote_site(...)`
- 逐目标探测，命中即 healthy；
- 返回新增字段：`checked_target`、`auth_mode`。

5. `upsert_remote_site(...)`
- 写入前校验并规范化 `auth_mode`。

## 3. 兼容性

1. 默认 `auth_mode=token` 行为不变。
2. 无数据库迁移。
3. 新增字段为返回增强，不破坏既有调用方。

## 4. 风险与缓解

1. 风险：basic 密钥格式不规范导致探活失败。
2. 缓解：支持多来源回退（metadata + secret）。
3. 风险：多目标探测增加请求成本。
4. 缓解：按固定顺序命中即停，保持短路。

## 5. 验收标准

1. basic auth + mirror 路径探活可成功。
2. token + 自定义 health_path 可成功。
3. 返回 `checked_target/auth_mode`。
4. 服务测试覆盖通过。
