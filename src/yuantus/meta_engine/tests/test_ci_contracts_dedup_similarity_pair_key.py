from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_similarity_record_has_pair_key_and_ingestion_is_concurrency_safe() -> None:
    repo_root = _find_repo_root(Path(__file__))
    models_py = repo_root / "src" / "yuantus" / "meta_engine" / "dedup" / "models.py"
    service_py = repo_root / "src" / "yuantus" / "meta_engine" / "dedup" / "service.py"

    models_text = _read(models_py)
    assert "pair_key" in models_text, "SimilarityRecord must have a pair_key column for unordered uniqueness."
    assert "uq_meta_similarity_records_pair_key" in models_text, (
        "SimilarityRecord must declare a unique constraint/index name for pair_key."
    )

    service_text = _read(service_py)
    assert "def _build_pair_key" in service_text, "DedupService must define _build_pair_key helper."
    assert "on_conflict_do_nothing(index_elements=[\"pair_key\"])" in service_text, (
        "Ingestion must insert SimilarityRecords with ON CONFLICT DO NOTHING on pair_key."
    )
