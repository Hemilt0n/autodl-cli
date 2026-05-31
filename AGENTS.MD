# AGENTS.MD

This file is for coding agents working on `autodl-cli`. Follow it before making changes.

## Project Scope

`autodl-cli` is a Python CLI for AutoDL Pro users.

Current implemented scope:

- AutoDL developer-token based authentication.
- Account balance lookup.
- Pro instance list, status, inspect, start, stop, release, destroy.
- Pro private image list and save.
- JSON output for script integration.
- Redaction of sensitive fields in user-facing output.

Explicitly out of current core scope:

- Enterprise Elastic Deployment API.
- Scraping AutoDL webpages or simulating browser login.
- Platform-wide physical machine lists or GPU inventory.
- Webhook, monitoring, scheduling, and resource-wait retry loops, unless the task explicitly asks to implement them.

When adding new features, keep the distinction between AutoDL Pro public API and Enterprise Elastic Deployment API clear in code, docs, and CLI help.

## Development Environment

Use `uv` for dependency and environment management.

Common commands:

```bash
uv sync
uv run autodl --help
uv run pytest
uv run ruff check .
```

Do not use ad hoc virtualenv or pip workflows unless the user explicitly asks. Keep `pyproject.toml` and `uv.lock` in sync when dependencies change.

## Code Organization

- `src/autodl_cli/app.py`: top-level Typer app, global options, command registration.
- `src/autodl_cli/config.py`: config file and token storage.
- `src/autodl_cli/constants.py`: shared constants.
- `src/autodl_cli/errors.py`: project exception hierarchy.
- `src/autodl_cli/output.py`: human/JSON output and redaction helpers.
- `src/autodl_cli/api/`: AutoDL API client and models.
- `src/autodl_cli/commands/`: Typer command groups.
- `tests/`: pytest tests for config, API client, and CLI behavior.
- `docs/autodl-pro-cli-design.md`: design notes and implementation plan.

Prefer small modules with clear ownership. Avoid mixing CLI presentation logic into the API client.

## API Rules

Use only documented AutoDL API endpoints unless the user explicitly requests research into a new endpoint.

Current public endpoints in use:

- `POST /api/v1/dev/wallet/balance`
- `POST /api/v1/dev/instance/pro/list`
- `GET /api/v1/dev/instance/pro/status`
- `GET /api/v1/dev/instance/pro/snapshot`
- `POST /api/v1/dev/instance/pro/power_on`
- `POST /api/v1/dev/instance/pro/power_off`
- `POST /api/v1/dev/instance/pro/release`
- `POST /api/v1/dev/instance/pro/image/save`
- `POST /api/v1/dev/instance/pro/image/private/list`

The API client should:

- Set `Authorization` to the developer token.
- Treat `code != "Success"` as an API error.
- Classify obvious auth and capacity errors into specific exception types.
- Keep raw HTTP handling out of command modules.
- Accept an `httpx` transport for tests.

## Safety and Billing

AutoDL Pro operations can create costs or destroy resources.

Treat these as billable or destructive:

- `instance start`
- `instance release`
- `instance destroy`

Testing rules:

- Do not run billable API calls against a real AutoDL account by default.
- Unit and CLI tests should use `httpx.MockTransport` or equivalent mocks.
- Any future real-integration test that creates, starts, stops, or releases instances must be opt-in and clearly documented.
- Do not print root passwords, Jupyter tokens, developer tokens, or Authorization headers.
- Keep secret redaction centralized in `output.py` or a dedicated helper.

## CLI Design

Use Typer for commands.

Global options should remain consistent:

- `--profile`
- `--config`
- `--base-url`
- `--token`
- `--json`
- `--version`

Command output should have two modes:

- Default: readable terminal output using Rich.
- `--json`: stable JSON suitable for scripts.

AI agents and automation should use `--json`, not Rich table output. Human-facing tables are optimized for readability and may change formatting.

For list commands, keep JSON field names stable and normalized. For example, `instance list --json` should expose `uuid`, `name`, `status`, `gpu_spec_uuid`, and `gpu_amount` even if AutoDL returns legacy or alternate field names.

For commands that may charge money or release resources, require confirmation unless a clear `--yes` flag is provided.

## Config and Token Storage

Configuration lives in a TOML file managed by `ConfigManager`.

Token storage order:

1. User-provided `--token`, never persisted.
2. System keyring.
3. Local token file fallback.

When writing token files, use owner-only permissions where the platform supports it.

Do not store tokens inside `config.toml` unless a future explicit design decision changes this.

## Testing Expectations

Before committing code changes, run:

```bash
uv run pytest
uv run ruff check .
```

Add or update tests when changing:

- API request paths or payloads.
- Error classification.
- Config serialization.
- Token loading behavior.
- CLI arguments or output shapes.
- Secret redaction.

Keep tests deterministic. Avoid network calls in default tests.

## Documentation Expectations

README is written for Chinese-speaking users and should stay beginner-friendly.

When adding user-facing commands:

- Update README with examples.
- Update `docs/autodl-pro-cli-design.md` if the design scope changes.
- Clearly label unimplemented or planned features.

Avoid English-only user docs unless the user asks for them.

## Git Practices

Work on the current branch unless the user asks to switch.

Commit in small, reviewable chunks:

- Dependency/config changes.
- Core implementation changes.
- Documentation changes.
- Test-only changes.

Do not batch unrelated changes into one large commit.

Never revert unrelated user or other-agent changes unless explicitly instructed.

## Style

- Python target: 3.11+.
- Keep type hints practical and readable.
- Prefer explicit request/response helpers over stringly-typed command code.
- Use Pydantic models for structured API/config data when useful.
- Keep comments sparse and focused on non-obvious behavior.
- Keep filenames and command names lowercase unless matching an external convention.

## Future Feature Notes

Planned but not core yet:

- Pro instance create. This was intentionally removed from the CLI until request parameters and real Pro behavior are revalidated.
- Feishu webhook notifications.
- Generic webhook notifications.
- Instance monitoring.
- Resource wait/retry for scarce compute.
- Scheduling and daemon mode.

When implementing these, build them as services under `src/autodl_cli/services/` or a similarly clear boundary, then expose them through `src/autodl_cli/commands/`.
