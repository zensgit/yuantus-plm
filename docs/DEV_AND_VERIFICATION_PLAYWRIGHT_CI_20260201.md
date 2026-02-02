# Playwright CI 集成 开发与验证（2026-02-01）

## 目标

- 将电子签名 Playwright CLI 验证纳入 CI，确保每次提交可自动回归。
- 补齐文档索引，方便交付与追溯。

## 关键实现

### 1) CI 集成

- 新增 `playwright-esign` 任务，执行 `npx playwright test`。
- CI 侧禁用浏览器下载（`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`），仅使用 API 测试。
- 依赖自动启动临时服务与种子数据（见 `playwright.config.js`）。

### 2) 文档索引补齐

- `docs/DELIVERY_DOC_INDEX.md` 增加 Phase 4/5 与 Phase 6 的开发验证入口。

## 主要文件

- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `playwright.config.js`
- `playwright/tests/esign.spec.js`

## 验证

### Playwright CLI

```bash
npx playwright test
```

- 结果：`PASS`（1 passed）
- 记录：`Run PLAYWRIGHT-ESIGN-20260201-2359`

## 备注

- CI 运行时会使用临时 DB `/tmp/yuantus_playwright.db`，不影响本地开发库。
