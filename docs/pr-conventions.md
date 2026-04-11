# PR Conventions

This page documents the branch naming, PR title, and label conventions used in this repository.

## Branch prefixes

Use these prefixes in branch names to indicate the purpose of the PR.

| Prefix | Purpose | Example |
| --- | --- | --- |
| `feat/` or `feature/` | New feature | `feat/game-sets-scraper` |
| `fix/` or `bugfix/` | Bug fix | `fix/login-timeout` |
| `hotfix/` | Urgent production fix | `hotfix/critical-auth-bug` |
| `chore/` | Maintenance, dependencies, config | `chore/update-dependencies` |
| `refactor/` | Code refactoring without new features | `refactor/cleanup-scrapers` |
| `docs/` | Documentation only | `docs/update-readme` |
| `test/` | Adding or updating tests | `test/add-payout-tests` |
| `style/` | Formatting or linting only | `style/fix-linting` |
| `perf/` | Performance improvements | `perf/optimize-batch-requests` |
| `ci/` | CI or automation changes | `ci/add-github-actions` |
| `build/` | Build system changes | `build/update-webpack` |
| `revert/` | Reverting a previous commit | `revert/feat-broken-feature` |
| `release/` | Release preparation | `release/v3.0.0` |
| `wip/` | Work in progress | `wip/experimental-api` |

## PR title format

Use a matching semantic prefix in the PR title:

- `feat: add market lineage checks`
- `fix: repair series pagination`
- `docs: add pr conventions`

## Labels

Use the closest available repo labels for the change:

- Documentation-only change -> `documentation`
- Feature, refactor, test, build, perf, or chore change -> `enhancement`
- Bug fix or hotfix -> `bug`
