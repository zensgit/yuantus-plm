# 设计文档：并行支线 P2 Breakage Helpdesk Provider HTTP Adapters

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：将 `Breakage -> Helpdesk` 从 stub-only 扩展到 provider HTTP adapter（Jira/Zendesk）。

## 1. 目标

1. 支持真实 HTTP provider 分发，保留 stub 模式兼容开发环境。
2. 提供统一 integration 配置模型（auth、timeout、TLS、headers）。
3. 将 provider 失败映射到结构化错误码，便于重试策略与运营分析。

## 2. 方案

## 2.1 服务层

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

新增能力：

1. provider/integration 归一化
- `_normalize_helpdesk_provider(...)`
- `_normalize_helpdesk_integration(...)`

2. HTTP 分发能力
- `_build_helpdesk_http_headers(...)`
- `_dispatch_helpdesk_provider_http(...)`
- `_dispatch_helpdesk_provider(...)`

3. 错误映射扩展
- `_map_helpdesk_provider_error(...)` 新增 HTTP 状态族映射：
  - `provider_rate_limited`
  - `provider_auth_error`
  - `provider_invalid_request`
  - `provider_http_server_error`
  - `provider_transport_error`

4. 主执行路径增强
- `run_helpdesk_sync_job(...)` 支持读取 integration 并执行 HTTP provider dispatch。
- `enqueue_helpdesk_stub_sync(...)` 支持 `integration_json` 入参并写入 payload。
- `_build_helpdesk_sync_job_view(...)` 增补 `integration_mode/integration_base_url/error_code/error_message`。

## 2.2 路由层

文件：`src/yuantus/meta_engine/web/parallel_tasks_router.py`

改造：

1. `BreakageHelpdeskSyncRequest` 新增 `integration_json`。
2. `POST /api/v1/breakages/{incident_id}/helpdesk-sync` 透传 integration 参数到服务层。

## 3. 兼容性

1. 默认 provider 仍为 `stub`，不影响既有调用。
2. 新增字段为可选，现有客户端 payload 不需修改。
3. 无数据库迁移。

## 4. 风险与缓解

1. 风险：真实 provider 接口波动导致同步失败率上升。
2. 缓解：错误码结构化映射 + 失败分类（transient/permanent）支撑自动重试。
3. 风险：integration 参数配置错误影响派单。
4. 缓解：入参归一化与强校验（mode/auth/timeout/base_url）。

## 5. 验收标准

1. Jira/Zendesk 在 `mode=http` 下可正确构造请求并回填 external_ticket_id。
2. HTTP/传输错误映射到稳定错误码。
3. 帮助台同步状态查询可看到 integration 关键信息。
4. 服务、路由、E2E 回归通过。
