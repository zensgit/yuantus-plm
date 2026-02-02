# Phase 6 电子签名 开发与验证（2026-02-01）

## 目标

- 实现符合 21 CFR Part 11 / EU Annex 11 的电子签名基础能力：签名原因、签名记录、清单与审计。
- 提供签名、验证、撤销、清单状态查询的 API。

## 关键实现

### 1) 电子签名模型与服务

- 新增模型：`SigningReason`、`ElectronicSignature`、`SignatureManifest`、`SignatureAuditLog`。
- 新增服务：`ElectronicSignatureService`（签名/验证/撤销/清单/原因）。
- 签名哈希采用 HMAC（密钥来自 `ESIGN_SECRET_KEY` 或回退到 `JWT_SECRET_KEY`）。

### 2) API 路由

- `/api/v1/esign/reasons`（POST/GET）
- `/api/v1/esign/sign`
- `/api/v1/esign/verify/{signature_id}`
- `/api/v1/esign/revoke/{signature_id}`
- `/api/v1/esign/items/{item_id}/signatures`
- `/api/v1/esign/manifests`（POST）
- `/api/v1/esign/manifests/{item_id}`（GET）

### 3) 迁移与注册

- 迁移文件：`migrations/versions/v1b2c3d4e7a0_add_esign_tables.py`
- Bootstrap 注册：`src/yuantus/meta_engine/bootstrap.py`
- FastAPI 注册：`src/yuantus/api/app.py`

## 主要文件

- `src/yuantus/meta_engine/esign/models.py`
- `src/yuantus/meta_engine/esign/service.py`
- `src/yuantus/meta_engine/web/esign_router.py`
- `src/yuantus/api/dependencies/auth.py`
- `src/yuantus/config/settings.py`
- `migrations/versions/v1b2c3d4e7a0_add_esign_tables.py`
- `playwright.config.js`
- `playwright/tests/esign.spec.js`

## 验证

### Playwright CLI

```bash
npx playwright test
```

- 结果：`PASS`（1 passed）
- 说明：使用临时 DB `/tmp/yuantus_playwright.db`，自动 seed identity/meta 后验证签名流程。
- 记录：`Run PLAYWRIGHT-ESIGN-20260201-2344`

## 备注

- 电子签名验证与撤销的审计日志已落库；后续可补充导出与检索接口。
