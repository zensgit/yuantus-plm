# Contributing

Thanks for improving YuantusPLM. This repo is a modular monolith with strict
verification scripts; please keep changes small and verifiable.

## Development setup

- Python 3.11+ recommended.
- Create a virtualenv and install editable deps:
  - `python3 -m venv .venv`
  - `. .venv/bin/activate`
  - `pip install -e .`

## Verification

- If you touch API, schema, or services, run:
  - `bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`

## Product Boundary And Contracts

- Yuantus owns workflows that mutate PLM object state.
- Metasheet should not become the source of truth for `item`, `BOM`, `version`,
  `ECO`, `approval`, or `release` state.
- If you add or change public PLM endpoints, treat that as a contract change and
  review:
  - `docs/WORKFLOW_OWNERSHIP_RULES.md`
  - `docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md`
- Workflow-related PRs should answer:
  - Does this change mutate PLM object state?
  - If yes, which Yuantus endpoint remains authoritative?
  - If no, why is this a non-PLM workflow and not PLM scope creep?

## Style

- Keep code readable and explicit.
- Prefer small, testable changes.

## License

By contributing, you agree that your contributions are licensed under the
Apache-2.0 license.
