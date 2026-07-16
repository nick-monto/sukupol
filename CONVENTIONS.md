# Sukupol Conventions

## Conventional Commits & Semantic Versioning

All changes MUST follow Conventional Commits 1.0.0
and Semantic Versioning 2.0.0.

Commit format: `<type>(<scope>): <description>` (space after colon is MANDATORY)

- `feat`: Minor version bump
- `fix`, `perf`: Patch version bump
- `docs`, `chore`, `style`, `refactor`, `test`: No bump unless breaking
- `BREAKING CHANGE:` or type `!`: Major version bump

## Git & Branch Workflow

- Never work directly on `main`. Every task starts with a feature branch via `kickoff-branch`.
- Integrate via `gh pr create` / `gh pr merge --squash`.
Use `land-branch.sh` for solo-local mode.
- Never push to `main`/`master` except via `land-branch.sh` (`GIT_BIGPOWERS_LAND=1`).
- Never call GitHub REST API directly (curl, fetch).
- Never include Co-authored-by footers for AI agents.
- Intermediate state commits should be squashed; keep git history clean.

## specs/ — All Planning Output Goes Here

Every skill that produces written output writes to `specs/`:

| File | Purpose |
| ------ | --------- |
| `specs/state.yaml` | Session state, active epic/story, handoff signals |
| `specs/release-plan.yaml` | Release index and epic list |
| `specs/execution-status.yaml` | Done/pending per story |
| `specs/product/*.yaml` | Scope, vision, glossary |
| `specs/epics/eNN-*.yaml` | Story/task plans with verify commands |
| `specs/tech-architecture/*` | Stack, design plans, ADRs |
| `specs/bugs/registry.yaml` | Bug tracking |

## Code Style

- Functions: 4–20 lines. Files: under 300 lines.
- One thing per function/module (SRP).
- Names specific, unique (grep < 5 hits).
- Explicit types everywhere. No `any`, no untyped public functions.
- Early returns over nested ifs. Max 2 levels of indentation.
- Extract shared logic. No magic strings or numbers.
- Remove dead code — don't comment it out. Boy Scout Rule applies.

## Comments

- Write WHY, not WHAT. Include provenance links for bug-driven changes.
- Docstrings on public functions: intent + one usage example.
- Never strip existing comments on refactor.

## Tests (F.I.R.S.T.)

- Every new function gets a test. Every bug fix gets a regression test.
- Tests must be Fast, Independent, Repeatable, Self-Validating, Timely.
- Cover edge cases: empty input, maximum, minimum, off-by-one.
- Assert on observable outcomes only — never internal state or private methods.
- One runnable verify command per story before marking done.

## Dependencies

- Inject through constructor/parameter, not global imports.
- Wrap third-party libs behind thin project-owned interfaces.

## Logging

- Structured JSON for debugging / observability.
- Plain text only for user-facing output.
