# Contributing to AgroSnap

## Workflow

1. Pick a task from [PHASES.md](PHASES.md). Work on one phase at a time.
2. Create a branch: `feat/<phase>-<short-name>`, `fix/<short-name>` or `docs/<short-name>`.
3. Before coding, list the files you intend to change in the PR description.
4. Keep changes focused. One concern per PR.
5. Run the checks below. Fix failures. Do not skip or silence tests.
6. Open a PR with: what changed, how it was tested (commands, devices, screenshots) and what remains.
7. Update PHASES.md status and the relevant docs in the same PR.

## Git workflow rules

These apply to every contributor, including AI coding agents.

1. Inspect `git status`, the current branch, recent commits and the existing code before making any changes.
2. Never overwrite or retrain existing ML checkpoints without the owner's explicit approval.
3. Work on exactly one small, independently testable task at a time.
4. Before each task, state the objective, the files you intend to change and the acceptance criteria.
5. Make the smallest change that accomplishes the objective. Avoid unrelated refactoring and unnecessary dependencies.
6. Run the relevant tests, linting, formatting and type checks. Report the actual results; never claim a check passed without running it.
7. Show a concise summary and the Git diff before committing.
8. Do not create a commit until the owner approves it. Never push to a remote unless explicitly asked.
9. Use conventional commit messages that describe one logical change.
10. If a check fails, fix the issue within the current task rather than moving on.
11. Keep every completed commit in a working state. If a change causes a regression, diagnose it and restore the last known-good state without discarding unrelated work.
12. Update PHASES.md and the relevant documentation when a task genuinely changes project status.

## Checks

```bash
# backend
cd backend && ruff check . && ruff format --check . && mypy app && pytest

# mobile
cd mobile && npx tsc --noEmit && npx eslint . && npm test
```

## Commit messages

Conventional Commits: `feat(scan): add photos tab picker`, `fix(api): reject truncated jpeg with 422`, `docs(model-card): add per-class results`.

## Rules that are never negotiable

- Never commit `.env` files, keys, tokens, passwords or model artifacts.
- Never overwrite or retrain existing ML checkpoints without the owner's approval.
- Never change preprocessing or class mapping without updating the parity fixtures and MODEL_CARD.md.
- Never add disease treatment text that is not from a reviewed source (ADVISORY_CONTENT.md).
- Never mark a task done, or a test passing, without evidence.

## Code style

- **Python:** Ruff (lint + format), type hints, Pydantic v2, SQLAlchemy 2.x style, async routes with sync TF work in a threadpool.
- **TypeScript:** strict mode, no `any` without a comment, function components and hooks, all strings through i18n.
