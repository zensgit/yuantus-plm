# Subcontracting-Governance-Docs Split Execution Card

Date: `2026-04-09`
Branch: `feature/claude-c43-cutted-parts-throughput`

This card is the first residual doc-only cleanup adjacent to the subcontracting
work, but intentionally outside the code-facing `subcontracting` split.

## Scope

Target files:

- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md`
- `docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md`
- `docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md`

## Execute

```bash
git switch -c docs/subcontracting-governance-pack
git status --short -- \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md \
  docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md
git add -- \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md \
  docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md
git diff --cached --stat
```

## Review

```bash
git diff --cached -- \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md \
  docs/DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md \
  docs/GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md
```

## Suggested Commit

- branch: `docs/subcontracting-governance-pack`
- commit title: `docs(subcontracting): split governance and operator pack`

## Rule

- keep this split doc-only
- do **not** reopen `src/yuantus/meta_engine/subcontracting/*`
- do **not** mix router-surface residual files into this branch
- keep launch checklist, operator playbook, and governance reading guide together

## Related References

- `docs/DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md`
- `docs/DIRTY_TREE_DOMAIN_COVERAGE_20260409.md`
- `docs/BRANCH_CLOSEOUT_SUMMARY_20260409.md`
