# autodl-cli

AutoDL Pro command-line tool.

Current status: core Pro account, instance, and image commands.

## Install

```bash
uv sync
uv run autodl --help
```

## Configure

Use a developer token from the AutoDL console.

```bash
uv run autodl init --token-store keyring
```

If keyring is unavailable on the host, store the token in a local user-only token
file:

```bash
uv run autodl init --token-store file
```

Useful global options:

```bash
uv run autodl --profile default --json account balance
uv run autodl --token "$AUTODL_TOKEN" account balance
```

## Core Commands

```bash
uv run autodl auth check
uv run autodl account balance

uv run autodl instance list
uv run autodl instance status <instance_uuid>
uv run autodl instance inspect <instance_uuid>
uv run autodl instance create --gpu-spec-uuid <gpu_spec_uuid> --image-uuid <image_uuid>
uv run autodl instance start <instance_uuid>
uv run autodl instance stop <instance_uuid>
uv run autodl instance release <instance_uuid> --yes
uv run autodl instance destroy <instance_uuid> --yes

uv run autodl image list
uv run autodl image save <instance_uuid> --name <image_name>
```

Secrets such as root passwords and Jupyter tokens are redacted from command
output by default.

## Development

This project is managed with `uv`.

```bash
uv run autodl --help
uv run pytest
uv run ruff check .
```

The implementation plan is in `docs/autodl-pro-cli-design.md`.
