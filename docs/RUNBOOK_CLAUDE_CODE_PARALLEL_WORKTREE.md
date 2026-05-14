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

Recommended non-interactive shape:

```bash
printf '%s\n' '<read-only prompt>' | claude -p --no-session-persistence --tools ""
```

Use read-only mode as the default whenever the active repo has local work, an
open PR, or a plan gate that could be misinterpreted by a second agent.

Read-only Claude Code output is advisory. It can identify risks, suggest a
scope, or review a staged diff, but it does not authorize implementation,
merge, phase transition, production cutover, or external evidence signoff.

### Worktree

Use this for implementation work. The printed command uses `claude --worktree`
so the sidecar writes in an isolated git worktree instead of the current tree.

Use worktree mode only after the user explicitly authorizes Claude Code to
write code for a bounded task. Keep the write set disjoint from active local
work, and have the primary agent review, test, and integrate the result before
opening or updating a PR.

### Reviewer

Use this when you only need a PR summary, reviewer checklist, or risk brief.
The runner script calls Claude Code in `-p` mode and keeps the session
read-only by instruction.

## Notes

- Prefer worktree mode for any write action.
- Keep sidecar scopes narrow and file-local when possible.
- Do not use the sidecar to clean unrelated dirty files in the current tree.
- Do not treat a Claude Code recommendation as a user opt-in to start a blocked
  phase. Phase gates still require explicit user authorization and the required
  evidence artifacts.
- Do not include secrets, webhook URLs, tokens, passwords, `.claude/`, or
  `local-dev-env/` in prompts, commits, review output, or indexed delivery
  docs.
- Do not bypass repository safety by using permission-skipping modes in the
  shared worktree. If write access is required, use an isolated worktree and
  keep the final integration under normal git review.
