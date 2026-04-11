# PR Conventions

Use these conventions when choosing the branch prefix, PR title prefix, and labels.

## Branch and title prefixes

Use the same prefix family for both the branch name and the PR title.

Format:

- branch: `<prefix>/<short-kebab-summary>`
- PR title: `<prefix>: <concise imperative summary>`

Prefer the short canonical prefixes in PR titles. Where aliases exist for branch names, normalize the PR title to the short form.

| Canonical prefix | Branch aliases | Purpose | Branch example | PR title example |
| --- | --- | --- | --- | --- |
| `feat` | `feat`, `feature` | New feature | `feat/game-sets-scraper` | `feat: add game sets scraper` |
| `fix` | `fix`, `bugfix` | Bug fix | `fix/login-timeout` | `fix: repair login timeout` |
| `hotfix` | `hotfix` | Urgent production fix | `hotfix/critical-auth-bug` | `hotfix: repair critical auth bug` |
| `chore` | `chore` | Maintenance, dependencies, config | `chore/update-dependencies` | `chore: update dependencies` |
| `refactor` | `refactor` | Refactoring without new behavior | `refactor/cleanup-scrapers` | `refactor: clean up scrapers` |
| `docs` | `docs` | Documentation only | `docs/update-readme` | `docs: update readme` |
| `test` | `test` | Test-only changes | `test/add-payout-tests` | `test: add payout tests` |
| `style` | `style` | Formatting or linting only | `style/fix-linting` | `style: fix linting` |
| `perf` | `perf` | Performance improvements | `perf/optimize-batch-requests` | `perf: optimize batch requests` |
| `ci` | `ci` | CI or automation changes | `ci/add-github-actions` | `ci: add github actions` |
| `build` | `build` | Build system changes | `build/update-webpack` | `build: update webpack` |
| `revert` | `revert` | Reverting a previous change | `revert/feat-broken-feature` | `revert: revert broken feature` |
| `release` | `release` | Release preparation | `release/v3-0-0` | `release: prepare v3.0.0` |
| `wip` | `wip` | Work in progress | `wip/experimental-api` | `wip: experimental api` |

## Label guidance

Inspect the repo's actual labels before applying them.

Prefer this mapping when the labels exist:

| Change type | Preferred labels |
| --- | --- |
| Documentation-only change | `documentation` |
| User-facing feature, refactor, test, perf, chore, or build improvement | `enhancement` |
| Bug fix or hotfix | `bug` |
| Mixed docs plus code change | combine `documentation` with `enhancement` or `bug` when both labels exist |

If the exact label does not exist, pick the closest available label and note the fallback.

## PR body guidance

Keep the PR body concise and operational:

1. Summary of what changed
2. Validation performed
3. Notes on review findings, follow-ups, or known risks
