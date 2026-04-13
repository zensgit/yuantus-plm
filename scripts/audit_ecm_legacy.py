#!/usr/bin/env python3
"""
PR-0.5: ECM Legacy Audit Script
================================
Audits the codebase and (optionally) the database to determine the scope
of the /ecm → /eco convergence effort.

Two audit modes:
  1. Code audit (always runs) — scans for all references to the legacy
     ChangeService, change_router, /ecm endpoints, and item_type_id="Affected Item".
  2. Database audit (runs with --db) — counts actual Affected Item rows
     and their action distribution.

Usage:
  python scripts/audit_ecm_legacy.py           # code audit only
  python scripts/audit_ecm_legacy.py --db      # code + database audit
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"

# Patterns to scan for legacy ECM usage
PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("ChangeService import", re.compile(r"from\s+.*change_service\s+import|import\s+.*change_service")),
    ("ChangeService instantiation", re.compile(r"ChangeService\s*\(")),
    ("/ecm endpoint reference", re.compile(r'["\'/]ecm[/"\']')),
    ('item_type_id="Affected Item"', re.compile(r"""item_type_id\s*==?\s*["']Affected Item["']""")),
    ("change_router import", re.compile(r"from\s+.*change_router\s+import|import\s+.*change_router")),
    ("change_router registration", re.compile(r"change_router")),
]

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".html", ".js", ".ts", ".md"}

# Directories to skip
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", "references"}

# Files to exclude from scan (self-references)
EXCLUDE_FILES = {"scripts/audit_ecm_legacy.py"}


# ---------------------------------------------------------------------------
# Code Audit
# ---------------------------------------------------------------------------

def scan_codebase() -> Dict[str, List[Tuple[str, int, str]]]:
    """Scan source tree for legacy ECM references.

    Returns:
        dict mapping pattern label → list of (file_path, line_no, line_text)
    """
    hits: Dict[str, List[Tuple[str, int, str]]] = defaultdict(list)

    for root, dirs, files in os.walk(REPO_ROOT):
        # Prune skip dirs in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix not in SCAN_EXTENSIONS:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue

            for lineno, line in enumerate(content.splitlines(), start=1):
                for label, pattern in PATTERNS:
                    if pattern.search(line):
                        rel = str(fpath.relative_to(REPO_ROOT))
                        if rel not in EXCLUDE_FILES:
                            hits[label].append((rel, lineno, line.strip()))

    return hits


def print_code_report(hits: Dict[str, List[Tuple[str, int, str]]]) -> None:
    print("=" * 72)
    print("ECM LEGACY CODE AUDIT")
    print("=" * 72)

    total = 0
    for label, matches in sorted(hits.items()):
        count = len(matches)
        total += count
        print(f"\n--- {label} ({count} hits) ---")
        for fpath, lineno, line in matches:
            print(f"  {fpath}:{lineno}  {line[:120]}")

    print(f"\n{'=' * 72}")
    print(f"TOTAL legacy ECM references: {total}")
    print("=" * 72)

    # Summary table: file → number of hits
    file_counts: Dict[str, int] = defaultdict(int)
    for matches in hits.values():
        for fpath, _, _ in matches:
            file_counts[fpath] += 1

    if file_counts:
        print("\nFiles with legacy ECM references (sorted by hit count):")
        for fpath, count in sorted(file_counts.items(), key=lambda x: -x[1]):
            print(f"  {count:3d}  {fpath}")


# ---------------------------------------------------------------------------
# Database Audit
# ---------------------------------------------------------------------------

def run_db_audit() -> None:
    """Query the database for Affected Item rows."""
    print(f"\n{'=' * 72}")
    print("ECM LEGACY DATABASE AUDIT")
    print("=" * 72)

    try:
        # Import project database utilities
        sys.path.insert(0, str(SRC_ROOT))
        from yuantus.database import get_database_url
        from sqlalchemy import create_engine, text

        url = get_database_url()
        engine = create_engine(url)

        with engine.connect() as conn:
            # Total count
            result = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM meta_items
                    WHERE item_type_id = 'Affected Item'
                """)
            )
            total = result.scalar() or 0
            print(f"\nTotal 'Affected Item' rows: {total}")

            if total == 0:
                print("  → No legacy data. Compat shim can be aggressive (thin or reject).")
                return

            # Action distribution
            result = conn.execute(
                text("""
                    SELECT
                        properties->>'action' AS action,
                        COUNT(*) AS cnt
                    FROM meta_items
                    WHERE item_type_id = 'Affected Item'
                    GROUP BY properties->>'action'
                    ORDER BY cnt DESC
                """)
            )
            rows = result.fetchall()
            print("\n  Action distribution:")
            for action, cnt in rows:
                print(f"    {action or '(null)':20s}  {cnt}")

            # Associated ECOs
            result = conn.execute(
                text("""
                    SELECT COUNT(DISTINCT source_id)
                    FROM meta_items
                    WHERE item_type_id = 'Affected Item'
                """)
            )
            eco_count = result.scalar() or 0
            print(f"\n  Distinct ECOs with Affected Items: {eco_count}")

            # ECO state distribution
            result = conn.execute(
                text("""
                    SELECT
                        e.state,
                        COUNT(DISTINCT a.source_id) AS eco_count,
                        COUNT(a.id) AS affected_count
                    FROM meta_items a
                    JOIN meta_items e ON e.id = a.source_id
                    WHERE a.item_type_id = 'Affected Item'
                    GROUP BY e.state
                    ORDER BY eco_count DESC
                """)
            )
            rows = result.fetchall()
            if rows:
                print("\n  ECO state breakdown:")
                print(f"    {'State':20s}  {'ECOs':>6s}  {'Affected Items':>15s}")
                for state, ecos, affected in rows:
                    print(f"    {state or '(null)':20s}  {ecos:6d}  {affected:15d}")

            # Age distribution
            result = conn.execute(
                text("""
                    SELECT
                        CASE
                            WHEN created_at > NOW() - INTERVAL '7 days' THEN 'last_7d'
                            WHEN created_at > NOW() - INTERVAL '30 days' THEN 'last_30d'
                            WHEN created_at > NOW() - INTERVAL '90 days' THEN 'last_90d'
                            ELSE 'older'
                        END AS age_bucket,
                        COUNT(*) AS cnt
                    FROM meta_items
                    WHERE item_type_id = 'Affected Item'
                    GROUP BY 1
                    ORDER BY 1
                """)
            )
            rows = result.fetchall()
            if rows:
                print("\n  Age distribution:")
                for bucket, cnt in rows:
                    print(f"    {bucket:20s}  {cnt}")

    except ImportError as e:
        print(f"\n  [SKIP] Cannot import database module: {e}")
        print("  Run with PYTHONPATH=src or from project root.")
    except Exception as e:
        print(f"\n  [ERROR] Database query failed: {e}")
        print("  This is expected if no database is running or table doesn't exist.")
        print("  The code audit above is the primary deliverable.")


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def print_recommendations(hits: Dict[str, List[Tuple[str, int, str]]]) -> None:
    print(f"\n{'=' * 72}")
    print("RECOMMENDATIONS FOR PR-1 / PR-2")
    print("=" * 72)

    # Identify files that need changes
    write_paths = set()
    test_files = set()
    for matches in hits.values():
        for fpath, _, _ in matches:
            if "/tests/" in fpath or fpath.startswith("tests/"):
                test_files.add(fpath)
            else:
                write_paths.add(fpath)

    print("\nFiles requiring changes in PR-1 (new canonical path):")
    for f in sorted(write_paths):
        if "change_service" in f or "change_router" in f or "workbench" in f:
            print(f"  [MODIFY] {f}")

    print("\nFiles requiring changes in PR-2 (compat shim):")
    for f in sorted(write_paths):
        if "change_router" in f:
            print(f"  [SHIM]   {f}")
        elif "change_service" in f:
            print(f"  [DEPRECATE] {f}")

    print("\nTest files requiring migration in PR-3:")
    for f in sorted(test_files):
        print(f"  [MIGRATE] {f}")

    print("\nRouter registration (app.py):")
    app_hits = [
        (f, l, t) for matches in hits.values()
        for f, l, t in matches
        if "app.py" in f
    ]
    for f, l, t in app_hits:
        print(f"  [REVIEW] {f}:{l}  {t}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit legacy ECM (/ecm, ChangeService, Affected Item) usage"
    )
    parser.add_argument(
        "--db", action="store_true",
        help="Also query the database for Affected Item row counts"
    )
    args = parser.parse_args()

    # Code audit (always)
    hits = scan_codebase()
    print_code_report(hits)

    # Database audit (optional)
    if args.db:
        run_db_audit()

    # Recommendations
    print_recommendations(hits)


if __name__ == "__main__":
    main()
