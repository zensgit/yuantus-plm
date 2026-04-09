# Claude Code Parallel Worktree Runbook

Use this runbook when you want to call Claude Code CLI as a sidecar without
mixing that work into the current dirty tree.

## Preconditions

- `claude auth status` returns `loggedIn: true`
- Current repo root is the directory you want Claude to inspect
- Write tasks should prefer a separate worktree

## Quick start

Print the recommended command templates:

```bash
bash scripts/print_claude_code_parallel_commands.sh
```

Print only the isolated worktree template:

```bash
bash scripts/print_claude_code_parallel_commands.sh --mode worktree --worktree-name claude-native-followup
```

Print only the read-only reviewer template:

```bash
bash scripts/print_claude_code_parallel_commands.sh --mode reviewer
```

Run the read-only reviewer sidecar immediately:

```bash
bash scripts/run_claude_code_parallel_reviewer.sh
bash scripts/run_claude_code_parallel_reviewer.sh --out /tmp/yuantus-review.txt
```

## Recommended modes

### Read-only

Use this for repo audits, reviewer briefs, change summaries, and scope checks.
It should not edit files.

### Worktree

Use this for implementation work. The printed command uses `claude --worktree`
so the sidecar writes in an isolated git worktree instead of the current tree.

### Reviewer

Use this when you only need a PR summary, reviewer checklist, or risk brief.
The runner script calls Claude Code in `-p` mode and keeps the session
read-only by instruction.

## Notes

- Prefer worktree mode for any write action.
- Keep sidecar scopes narrow and file-local when possible.
- Do not use the sidecar to clean unrelated dirty files in the current tree.
