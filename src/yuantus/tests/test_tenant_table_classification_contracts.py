from __future__ import annotations

import re
from pathlib import Path

from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES, build_tenant_metadata


REPO_ROOT = Path(__file__).resolve().parents[3]
CLASSIFICATION_DOC = REPO_ROOT / "docs" / "TENANT_TABLE_CLASSIFICATION_20260427.md"


def _read_doc() -> str:
    assert CLASSIFICATION_DOC.is_file()
    return CLASSIFICATION_DOC.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    assert start != -1, f"missing heading: {heading}"
    start = text.find("\n", start) + 1
    end = text.find("\n## ", start)
    if end == -1:
        end = len(text)
    return text[start:end]


def _listed_tables(section: str) -> set[str]:
    return set(re.findall(r"^- `([^`]+)`$", section, flags=re.MULTILINE))


def test_table_classification_artifact_exists_and_is_not_signed_off() -> None:
    text = _read_doc()

    assert "Status: **classification artifact created; sign-off pending**." in text
    assert re.search(r"does \*\*not\*\* authorize\s+P3\.4", text)
    assert "No `TENANCY_MODE=schema-per-tenant` enablement." in text


def test_global_table_section_matches_runtime_global_table_names() -> None:
    text = _read_doc()
    section = _section(text, "## 3. Global / Control-Plane Tables (15)")

    assert _listed_tables(section) == set(GLOBAL_TABLE_NAMES)
    assert f"({len(GLOBAL_TABLE_NAMES)})" in "## 3. Global / Control-Plane Tables (15)"


def test_tenant_table_section_matches_runtime_tenant_metadata() -> None:
    text = _read_doc()
    tenant_names = set(build_tenant_metadata().tables)
    section = _section(text, f"## 4. Tenant Application Tables ({len(tenant_names)})")

    listed = _listed_tables(section)
    assert listed == tenant_names
    assert listed.isdisjoint(GLOBAL_TABLE_NAMES)


def test_p34_stop_gate_remains_blocked_except_merged_p33_items() -> None:
    text = _read_doc()
    section = _section(text, "## 5. P3.4 Stop-Gate Status")

    required_open_items = [
        "A non-production PostgreSQL target DSN is provisioned.",
        "A named pilot tenant is identified and approved.",
        "A backup/restore owner is named.",
        "A migration rehearsal window is scheduled.",
        "This table classification artifact is reviewed and signed off.",
    ]
    for item in required_open_items:
        assert f"- [ ] {item}" in section

    assert (
        "- [x] P3.3.1, P3.3.2, and P3.3.3 are merged and post-merge smoke green."
        in section
    )
