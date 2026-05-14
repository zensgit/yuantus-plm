# Dev & Verification - Claude Code Assist Discipline

Date: 2026-05-14

## 1. Summary

Documented and CI-pinned how this repository should use Claude Code as an
assistant after the post-P6 / post-exception-chaining closeout state.

Claude Code can be used, but the default mode is read-only assistance. Its
output is advisory and does not replace explicit user opt-in, phase gates,
review, verification, or merge decisions.

## 2. Why This Exists

The project now has several local gates:

- Phase 5 remains blocked by accepted real P3.4 external PostgreSQL rehearsal
  evidence.
- `.claude/` and `local-dev-env/` are local-only and must not be committed.
- Recent continuation work benefits from Claude Code as a reviewer sidecar, but
  uncontrolled write access in the shared worktree would create avoidable merge
  and provenance risk.

This PR turns that operating discipline into a runbook section and a CI-backed
contract.

## 3. Files Changed

- `docs/RUNBOOK_CLAUDE_CODE_PARALLEL_WORKTREE.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_assist_discipline.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_CLAUDE_CODE_ASSIST_DISCIPLINE_20260514.md`

## 4. Rules Pinned

1. Read-only Claude Code is the default for audits, risk checks, staged-diff
   review, and scope selection.
2. Claude Code recommendations are advisory; they do not authorize
   implementation, merge, phase transition, production cutover, or evidence
   signoff.
3. Claude Code write work requires explicit user authorization and an isolated
   worktree or otherwise bounded write set.
4. The primary agent remains responsible for reviewing, testing, integrating,
   and opening/updating PRs.
5. `.claude/`, `local-dev-env/`, secrets, webhook URLs, passwords, and tokens
   stay out of prompts, commits, review output, and indexed delivery docs.
6. Phase 5 remains blocked until accepted real P3.4 external PostgreSQL
   rehearsal evidence is recorded.

## 5. Claude Code Assist

Claude Code was used read-only for this slice. It recommended the docs +
contracts discipline over starting Phase 5/P3.4 or doing another runtime slice.
It did not edit files.

## 6. Non-Goals

- No runtime code changes.
- No Phase 5 implementation.
- No P3.4 evidence synthesis or cutover enablement.
- No database, migration, tenant provisioning, scheduler, CAD plugin, or
  external-service behavior change.
- No change to the existing Claude Code helper scripts.

## 7. Verification Commands

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_assist_discipline.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_assist_discipline.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_claude_code_parallel_helper.py \
  src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python - <<'PY'
import ast
from pathlib import Path

root = Path(".").resolve()
exception_names = {"e", "exc", "err", "ex", "error", "exception"}

def contains_exception_ref(node):
    return any(
        isinstance(child, ast.Name) and child.id in exception_names
        for child in ast.walk(node)
    )

def is_stringified(node):
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"str", "repr"}
    ):
        return any(contains_exception_ref(arg) for arg in node.args)
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(value, ast.FormattedValue)
            and contains_exception_ref(value.value)
            for value in node.values
        )
    return False

def is_http_exception(node):
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id == "HTTPException"
    return isinstance(node.func, ast.Attribute) and node.func.attr == "HTTPException"

offenders = []
for path in sorted((root / "src/yuantus").rglob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        if node.cause is not None or not is_http_exception(node.exc):
            continue
        detail = next(
            (keyword.value for keyword in node.exc.keywords if keyword.arg == "detail"),
            None,
        )
        if detail is not None and is_stringified(detail):
            offenders.append(f"{path.relative_to(root)}:{node.lineno}")
print("no offenders" if not offenders else "\\n".join(offenders))
PY

git diff --check
```

## 8. Verification Results

- `py_compile` on the new contract: passed.
- Focused suite:
  - Claude Code assist discipline contract
  - Claude Code parallel helper contract
  - post-P6 plan-gate contract
  - doc-index trio
  - CI list-order contract
  - Result: `17 passed`.
- repo-wide HTTPException scan: no offenders.
- `git diff --check`: clean.

## 9. Review Checklist

- Confirm this PR is docs/contracts/CI wiring only.
- Confirm the runbook keeps Claude Code read-only by default.
- Confirm Claude Code output is advisory and cannot start Phase 5/P3.4.
- Confirm write-mode Claude Code requires explicit user authorization and an
  isolated/bounded write set.
- Confirm no `.claude/`, `local-dev-env/`, or secrets are indexed or staged.

This file is indexed as
`docs/DEV_AND_VERIFICATION_CLAUDE_CODE_ASSIST_DISCIPLINE_20260514.md`.
