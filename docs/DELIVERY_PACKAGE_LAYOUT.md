# Delivery Package Layout

This is a recommended directory layout for customer delivery bundles.

```
YuantusPLM-Delivery/
├── README.md
├── compose/
│   ├── docker-compose.yml
│   ├── docker-compose.mt.yml
│   └── docker-compose.no-cad-extractor.yml
├── env/
│   ├── .env.example
│   ├── .env.mt.example
│   └── .env.prod.example
├── scripts/
│   ├── mt_migrate.sh
│   ├── backup.sh
│   ├── restore.sh
│   ├── verify_run_h.sh
│   └── verify_permissions.sh
├── docs/
│   ├── OPS_RUNBOOK_MT.md
│   ├── DELIVERY_READINESS_CHECKLIST.md
│   ├── PRODUCT_DETAIL_FIELD_MAPPING.md
│   └── VERIFICATION_RESULTS.md
├── images/
│   ├── yuantus-api_v0.1.3.tar
│   └── yuantus-worker_v0.1.3.tar
├── certs/
│   ├── tls.crt
│   └── tls.key
└── licenses/
    └── LICENSE.txt
```

## Notes

- `compose/`: baseline + optional overlays.
- `env/`: environment templates, do **not** ship secrets.
- `scripts/`: migration/backup/verification helpers.
- `docs/`: ops and verification references.
- `images/`: optional offline Docker image tarballs (`docker save`).
- `certs/`: TLS material for reverse proxy.
- `licenses/`: license and third‑party notices.

## Optional

- Add `samples/` for seed data or demo CAD files.
- Add `configs/` for connector / extractor configs.
