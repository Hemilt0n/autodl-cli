from __future__ import annotations

import typer

from autodl_cli.app import manager_from_ctx
from autodl_cli.output import print_json

app = typer.Typer(help="Configuration commands.", no_args_is_help=True)


@app.command("path")
def path(ctx: typer.Context) -> None:
    """Print the config file path."""
    typer.echo(str(manager_from_ctx(ctx).config_path))


@app.command("show")
def show(ctx: typer.Context) -> None:
    """Show non-secret configuration."""
    config = manager_from_ctx(ctx).load().model_dump(mode="python")
    print_json(config)
