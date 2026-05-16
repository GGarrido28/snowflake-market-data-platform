---
name: code-change-pr-workflow
description: "End-to-end workflow for git-tracked code changes that should ship through GitHub with disciplined branch, commit, PR, review, and metadata handling. Use when Codex is asked to implement or update code in a repository and should: sync main safely, create a correctly prefixed branch, open or update a PR, commit work to that PR, delegate an independent code review, and use a documentation-focused agent to apply the right PR title and labels."
---

# Code Change PR Workflow

Use this skill to run the full GitHub delivery flow for code changes, not just the code edit itself. Treat branch naming, PR creation, review delegation, and PR metadata as part of the task.

Read [references/pr-conventions.md](references/pr-conventions.md) before naming the branch or PR.

## Workflow

### 1. Sync `main` safely

Fetch from `origin` first.

Prefer this sequence when the worktree allows it:

```text
git fetch origin
git switch main
git pull --ff-only origin main
```

If switching to `main` would disturb local work, do not reset, discard, or overwrite anything. Instead, branch from `origin/main` directly and note that `main` was verified via fetch rather than checked out locally.

### 2. Create a new branch

Choose the branch prefix from [references/pr-conventions.md](references/pr-conventions.md).

Format the branch name as:

```text
<prefix>/<short-kebab-summary>
```

Examples:

```text
feat/add-market-lineage-tests
fix/repair-series-pagination
docs/add-pr-conventions
```

Prefer `git switch -c <branch>` from updated `main`. If branching from fetched remote state because the local worktree is busy, use a safe non-destructive alternative.

### 3. Create the PR early

Push the branch and create the PR as soon as the branch has a real diff that GitHub can open. In practice, this often means after the first checkpoint commit, because a PR generally needs a pushed branch with changes.

Prefer `gh pr create` and open the PR in draft mode if the implementation is still in progress.

If a user explicitly wants the PR opened before the bulk of implementation, create a small truthful checkpoint commit rather than an empty misleading one.

### 4. Implement and commit changes to the PR

Make the requested code changes.

Run targeted validation before the final commit whenever feasible.

Create focused commits with honest messages. Avoid rewriting unrelated history unless the user asks.

Push follow-up commits to the same branch so they land on the same PR.

### 5. Spawn an independent review agent

If subagents are available and permitted in the current Codex environment, spawn an independent agent to review the PR diff for bugs, regressions, data-contract issues, and missing tests.

Keep the review prompt focused on findings first. Do not ask the review agent to rewrite the code unless the user requests that separately.

If subagents are unavailable in the current environment, perform a local review pass and state that you used a fallback.

### 6. Spawn a documentation or metadata agent

If subagents are available and permitted, spawn a second agent whose job is PR metadata only:

- verify the branch prefix
- propose or apply the PR title with the matching title prefix
- inspect available repository labels
- apply the correct labels to the PR
- tighten the PR summary or body if needed
- link to relevant documentation or issue tracking if applicable

Keep this agent out of code changes unless the user explicitly asks for documentation edits in the repo itself.

If subagents are unavailable, do the metadata pass locally and state that you used a fallback.

## Metadata rules

Use the same semantic prefix family for the branch and PR title.

Examples:

- branch `feat/add-series-loader` -> PR title `feat/add-series-loader`
- branch `fix/repair-orderbook-keying` -> PR title `fix/repair-orderbook-keying`
- branch `docs/add-entity-map` -> PR title `docs/add-entity-map`

Inspect the repo's actual labels before applying them. Do not assume a label exists.

## Completion checklist

Before closing out the task, confirm that you have covered these items:

1. `main` verified against `origin/main`
2. new branch created with the right prefix
3. PR opened or updated
4. commits pushed to that PR branch
5. independent review completed or explicit fallback noted
6. title prefix and labels applied or explicit fallback noted
