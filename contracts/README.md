# Integration Contracts

This folder contains JSON Schemas used as integration contracts between Yuantus
and external services.

Current schemas:
- dedupcad_vision_search_v2.schema.json
- cad_ml_vision_analyze.schema.json
- cad_extractor_extract.schema.json

Usage:
- Consumer-side validation lives in `src/yuantus/integrations/tests/test_contract_schemas.py`.
- Provider-side validation can reuse these schemas in API tests.
