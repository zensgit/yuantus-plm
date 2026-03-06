# 开发与验证：并行支线 P2 Version Checkout Doc-Sync Gate Scope Extension

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 设计文档：`docs/DESIGN_PARALLEL_P2_VERSION_CHECKOUT_DOC_SYNC_GATE_SCOPE_EXT_20260306.md`

## 1. 本轮开发范围

1. `evaluate_checkout_sync_gate` 支持 `version_id/document_ids`。
2. checkout 路由支持 `doc_sync_document_ids`，并自动采集 version 附件 ID。
3. 门禁返回增加 `monitored_document_ids/matched_document_ids`。
4. 增加服务和路由测试覆盖。

## 2. 变更文件

- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/web/version_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py`
- `docs/DESIGN_PARALLEL_P2_VERSION_CHECKOUT_DOC_SYNC_GATE_SCOPE_EXT_20260306.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_P2_VERSION_CHECKOUT_DOC_SYNC_GATE_SCOPE_EXT_20260306.md`

## 3. 验证命令

```bash
pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k "checkout_gate"
```

```bash
pytest -q src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py
```

## 4. 验证结果

1. checkout gate 服务聚焦：`2 passed`
2. version checkout 门禁路由：`4 passed`

## 5. 结论

checkout 门禁已扩展到版本/附件粒度，支持更细粒度阻断控制并保持原有兼容行为。
