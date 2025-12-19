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

## Style

- Keep code readable and explicit.
- Prefer small, testable changes.

## License

By contributing, you agree that your contributions are licensed under the
Apache-2.0 license.
