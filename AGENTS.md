# Codex Repository Instructions

## Project identity

TicoMon is a game engine whose first interface is Discord. Discord is an
interface, not part of the domain. The Core must be testable without Discord,
Railway, or PostgreSQL.

## Architecture and dependencies

- `core/`: game-domain rules and objects. It does not import Discord or
  persistence and external infrastructure details.
- `application/`: orchestrates use cases and coordinates Core services with
  repositories and ports.
- `infrastructure/`: implements persistence and external services, including
  PostgreSQL/Neon and their mappers.
- `interfaces/discord/`: cogs, views, buttons, and interaction adapters. It
  converts Discord input into Application/Core calls and presents their
  results.
- `rendering/`: presentation renderers and visual resources. It must not own
  business rules.
- `test/`: tests organized by layer, with doubles and fakes for unit tests.

Dependencies point toward the Core. Application may orchestrate the Core;
Infrastructure implements application contracts; Discord depends on
Application/Core to interact with the game. Do not add reverse imports from
Core to Discord, Infrastructure, or database details.

The Core returns domain objects and results, never Discord embeds, views, or
components. Every datum has one source of truth, and business rules must not
be duplicated between layers.

Normal Spawn and Safari are separate systems. Regional forms are exclusive to
Safari. Reuse existing species and variant resolvers and catalogs; do not keep
parallel lists.

## Implementation philosophy

- Solve the current problem, not hypothetical future scenarios.
- Avoid overengineering, premature abstractions, and unrequested refactors.
- Prefer small, direct, and verifiable changes.
- Reuse existing patterns when they are appropriate.
- Do not introduce layers, services, tables, configuration, or dependencies
  without demonstrated need.
- Do not modify modules outside the approved scope unless indispensable.
- Do not add functionality the user did not request.
- Prefer clarity over clever code.
- Before assigning a responsibility, determine which module owns that
  knowledge.
- Do not change weights, capture, persisted data, or balance outside the
  explicit task scope.

## Testing and validation

The project uses Python 3.11 and Poetry. The bootstrap confirmed by the
project and CI is:

```powershell
poetry install --no-interaction
```

Validation commands:

```powershell
poetry run pytest -q path/to/test_file.py
poetry run ruff check .
poetry run black --check .
git diff --check
pre-commit run --files <changed-files>
```

The full local suite uses:

```powershell
poetry run pytest -q
```

The `python scripts/check_all.py` script runs the test suite only:

```powershell
python scripts/check_all.py
```

The CI unit validation, without Neon tests, is:

```powershell
poetry run pytest -q -m "not neon_db"
```

With `NEON_DATABASE_URL` available, Neon tests run as follows:

```powershell
poetry run pytest -q -m neon_db
```

CI is defined in `.github/workflows/ci.yml`. It uses Python 3.11, installs
with Poetry, runs Ruff and Black in `lint`, the `not neon_db` suite in
`unit-tests`, and `neon_db` conditionally in `neon-tests`. Pre-commit is an
additional local validation, not a separate CI job.

Recommended order: inspect Git state, run focused tests, Ruff, Black,
`git diff --check`, pre-commit, and then the full suite. If a tool reformats
files, review the diff, keep only intended changes, and repeat validation.
Never hide, ignore, or disable failed tests.

Current configuration is in `pyproject.toml` and `.pre-commit-config.yaml`.
Black and Ruff use line length 88 and target Python 3.11; pytest discovers
tests under `test/` and defines the `neon_db` marker.

## Test rules

- Every behavior change must have tests.
- Prefer Core unit tests.
- Do not depend on Discord, Railway, or external services to validate domain
  rules.
- Run focused tests for the changed module first, then the full suite.
- Do not alter tests merely to make an incorrect implementation pass.

## Git workflow

- Inspect the initial Git state before modifying files.
- Do not overwrite other people's changes.
- Keep the diff limited to the approved scope and review it before committing.
- Run all required validation.
- When the requested change is complete and validated, create the commit
  directly without asking for additional permission.
- Use a conventional and descriptive commit message.
- Stop after the commit.
- Do not push unless explicitly instructed.
- Report the hash, message, included files, validations, and final working-tree
  state.

## Ambiguity

- Inspect existing code, tests, and documentation first.
- Choose the smallest solution compatible with the current design.
- Do not turn a limited task into a redesign.
- Mention relevant assumptions in the final summary.
- Stop and explain the conflict when a request contradicts a domain rule or
  implies data loss.
