# DEV / Verification - Security Audit Head Review

日期：2026-04-20
复核基线：`0e02d9c`（`Merge pull request #283 from zensgit/docs/shared-dev-142-workflow-success-validation-20260420`）
外部输入：`/Users/chouhua/Downloads/deep-research-report.md`

## 目标

对外部审计文档 `deep-research-report.md` 做一轮基于当前 `main` HEAD 的工程复核。

本文件不重复原报告全文，只回答三件事：

1. 哪些问题在当前 HEAD 仍然成立
2. 哪些问题需要收窄表述
3. 哪些结论还缺少当前代码上的直接证据

## 结论摘要

总体判断：

- 报告抓到的主风险方向是对的
- 但它把“代码默认值风险”、“参考部署风险”和“当前可直接利用性”混写了
- 因此更适合作为整改输入，而不是原样作为最终审计结论发出

按当前 HEAD 复核后，我的结论是：

- 当前成立：4 项
- 部分成立但需收窄：3 项
- 证据不足或需要补 PoC：2 项

## 当前仍成立

### 1. 默认认证仍然是 `optional`

当前默认配置仍然是：

- `AUTH_MODE="optional"`，[settings.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/config/settings.py:209)
- `JWT_SECRET_KEY` 也仍是 dev 默认值，[settings.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/config/settings.py:212)

这意味着：

- 如果部署方没有显式覆盖，系统不会 fail-closed
- 风险的根源是“安全默认值偏宽松”，这一点报告判断成立

### 2. 匿名用户仍然会回退到 `user_id=1`

当前实现仍然是：

- `get_current_user_id_optional()` 在 `user is None` 时返回 `1`，[auth.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/dependencies/auth.py:314)

这会带来两个确定问题：

- 匿名请求与真实用户 `1` 的审计归属被混在一起
- 任何依赖该 helper 的写接口，都天然带有“默认身份漂移”风险

这一点不需要推演，当前代码就是如此。

### 3. `/jobs` 路由设计确实过宽，且 diagnostics 暴露内部路径

当前 `jobs` 路由仍然有三处明显问题：

- `POST /jobs` 依赖 `get_current_user_id_optional()`，[jobs.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/routers/jobs.py:153)
- `GET /jobs/{job_id}` 没有路由级身份依赖，[jobs.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/routers/jobs.py:192)
- `GET /jobs` 同样没有路由级身份依赖，[jobs.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/routers/jobs.py:202)

同时，diagnostics 仍会回显：

- `system_path`
- `resolved_source_path`
- `preview_path`
- `geometry_path`
- CAD manifest / document / metadata / BOM 路径

见 [jobs.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/routers/jobs.py:74)。

因此报告把 `/jobs` 识别为高风险控制面，这一方向成立。

### 4. FreeCAD 动态脚本生成仍然存在注入面

当前 FreeCAD 路径仍然是把输入直接拼进 Python 源码：

- `_generate_freecad_script()` 直接把 `input_path` / `output_path` / `target_format` 塞进 f-string，[cad_converter_service.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/cad_converter_service.py:421)
- `_freecad_preview()` 同样直接把 `source_path` / `output_path` 写进脚本，[cad_converter_service.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/cad_converter_service.py:599)
- 生成目录仍然使用原始 `filename` 的 stem，[cad_converter_service.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/cad_converter_service.py:737)

所以“代码生成输入未转义”的核心判断成立。

## 部分成立，但需要收窄表述

### 1. “`/jobs` 匿名可打”依赖运行模式，不应写成无条件现状

报告把 `/jobs` 描述为匿名即可直接创建、枚举、查看。

这在“代码默认值层面”是危险的，但在“参考部署层面”需要收窄：

- 参考 `docker-compose.yml` 已把 `YUANTUS_AUTH_MODE` 设为 `required`，[docker-compose.yml](/Users/chouhua/Downloads/Github/Yuantus/docker-compose.yml:91)
- 全局 `AuthEnforcementMiddleware` 会在 `required` 模式下统一拦截无 token 请求，[auth_enforce.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/middleware/auth_enforce.py:76)

因此更准确的说法应是：

- `/jobs` 的路由设计本身过宽
- 在 `AUTH_MODE=optional` 或错误部署时会直接暴露
- 在参考 compose 部署下，未认证匿名流量会先被全局中间件挡住

### 2. “跨租户越权已证实”这个表述太满

当前链条里确实存在危险组合：

- 默认 `AUTH_MODE=optional`
- `TenantOrgContextMiddleware` 会接受头部里的 tenant/org，[context.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/middleware/context.py:11)
- `get_db()` 在多租户模式下按上下文分库，[database.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/database.py:174)
- 匿名用户又会回退到 `user_id=1`，[auth.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/dependencies/auth.py:314)

但要把它升级成“当前已证实的跨租户漏洞”，还缺两步：

1. 指定 tenancy mode
2. 给出当前 HEAD 下可复现的具体路由 PoC

所以这里更准确的标签应是：

- 高风险设计缺陷：成立
- 当前已证实跨租户 exploit：证据还不够

### 3. “前三项上线即踩坑”也偏绝对

对默认值和错误部署来说，这句话是合理警告。

但如果指参考仓库提供的 compose 栈，它已经至少做了两件保护：

- API 主服务 auth 默认 `required`
- shared-dev / observation 路径最近也已经补齐了 workflow secret 与验证闭环

因此“上线即踩坑”应改成：

- 若按默认代码值或宽松部署运行，会很快踩坑
- 若按当前参考 compose 运行，匿名直打面已经被部分收窄，但内部控制面设计仍需整改

## 证据不足或需要补强

### 1. `urllib3` 依赖漏洞结论应单独复核后再对外发布

当前仓库确实锁在：

- `urllib3==1.26.20`，[requirements.lock](/Users/chouhua/Downloads/Github/Yuantus/requirements.lock:57)

这足以说明“版本偏旧，需要安全复核”。

但如果要把具体 GHSA/CVE 直接写进最终审计摘要，建议在正式对外版里再做一次独立校验，而不是只继承外部报告。

当前 HEAD 复核结论可以保守写成：

- `urllib3` 版本仍在应重点复核区间
- 升级到安全版本并做兼容性回归是合理动作

### 2. “未发现后门/时间炸弹”不能算强结论

报告里这句更像人工抽样后的经验判断，不是完整的恶意代码审计结论。

我同意目前没有看到明显恶意逻辑，但如果要把它作为正式结论，需要额外证据，例如：

- 更系统的动态/静态规则扫描
- 插件目录与动态脚本生成面专项排查
- CI / vendor wheels / plugins 的来源校验

## 其他确认项

### 1. 部署默认值问题成立

`docker-compose.yml` 中仍然存在：

- `minioadmin` 默认口令，[docker-compose.yml](/Users/chouhua/Downloads/Github/Yuantus/docker-compose.yml:88)
- `change-me-in-production` JWT secret，[docker-compose.yml](/Users/chouhua/Downloads/Github/Yuantus/docker-compose.yml:92)
- 明文 `http://` 内部端点，[docker-compose.yml](/Users/chouhua/Downloads/Github/Yuantus/docker-compose.yml:84)
- dedup vision 默认 `INTEGRATION_AUTH_MODE=disabled`，[docker-compose.yml](/Users/chouhua/Downloads/Github/Yuantus/docker-compose.yml:276)
- cad-extractor 默认 `CAD_EXTRACTOR_AUTH_MODE=disabled`，[docker-compose.yml](/Users/chouhua/Downloads/Github/Yuantus/docker-compose.yml:293)

所以“部署默认值偏危险”成立。

### 2. 插件自动加载风险成立

当前默认配置仍然是：

- `PLUGIN_DIRS="./plugins"`，[settings.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/config/settings.py:274)
- `PLUGINS_AUTOLOAD=True`，[settings.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/config/settings.py:277)

运行时会自动 discover / load / activate，并把路由挂到 `/api/v1`，[runtime.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/plugin_manager/runtime.py:48)。

因此它确实属于供应链/扩展面风险，不应在生产默认开启。

### 3. `/integrations/health` 中风险判断成立

当前路由仍然：

- 未绑定身份依赖，[integrations.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/routers/integrations.py:34)
- 返回 `base_url`、错误体与服务健康信息，[integrations.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/api/routers/integrations.py:17)

这一项作为“内部服务枚举/信息泄露”中风险是成立的。

## 我的最终意见

如果这份外部报告要继续用，我建议这样处理：

1. 保留它作为“风险输入”
2. 不要原样转发为“当前正式审计结论”
3. 改成两层文档：
   - 外部报告原文
   - 当前 HEAD 复核结论

当前最应该优先处理的仍然是 P0 四项：

1. 去掉匿名 `user_id=1` 回退
2. 收紧 `/jobs` 控制面与 diagnostics
3. 重写 FreeCAD 参数传递，停止拼接 Python 源码
4. 让默认部署更接近 fail-closed，而不是靠运维记得覆盖

## 建议后续动作

如果要把这次复核继续转成工程动作，我建议下一步直接开一个安全整改包，拆成 3 个 PR：

1. `auth`: 去掉 `get_current_user_id_optional -> 1`
2. `jobs`: 全路由鉴权 + diagnostics 收缩
3. `cad`: FreeCAD 参数化，去掉动态脚本注入面

这三项比继续扩写报告更有价值。
