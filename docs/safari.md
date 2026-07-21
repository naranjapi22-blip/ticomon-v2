# Safari

## Player flow

- Unlock Safari through the existing game flow.
- Use `!safari` to open registration.
- Join, then start the expedition once at least two trainers are registered.
- During encounters, select a slot, choose 1-3 Balls, then confirm or decline.
- Resolve the encounter when selection closes.
- Vote on route options with visible route buttons when the session enters
  route decision. A trainer can replace their vote before the vote closes.
- Finish the expedition to view the final summary.
- Use the Pokédex button in Safari encounters to inspect caught or missing species.

## Development

- Safari logic lives in `core/safari` and `application/safari`.
- Discord only presents the existing Application results.
- Sessions, encounters, and route votes are kept in memory.
- Captures, Candies, and creatures persist through the existing capture boundary.
- Rendering lives in `rendering/safari`.
- Simulation lives in `simulation/safari`.

## Operations

- Create schema with the existing scripts under `scripts/`.
- Safari unlocks remain persisted in PostgreSQL.
- Safari sessions are currently in-memory and do not survive bot restarts.
- Watch structured logs for Safari open, start, encounter, route, and finish events.
- Use the simulator for balance analysis; it is read-only and does not write production data.
- Run `poetry run ruff check .`, `poetry run black --check .`, and `poetry run pytest -q -m "not neon_db"` before pushing changes.
- Use `poetry run python scripts/check_all.py` when you only need the test suite.
