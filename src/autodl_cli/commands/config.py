from __future__ import annotations

import typer

from autodl_cli.app import manager_from_ctx
from autodl_cli.output import print_json

app = typer.Typer(help="配置相关命令。", no_args_is_help=True)


@app.command("path")
def path(ctx: typer.Context) -> None:
    """显示配置文件路径。"""
    typer.echo(str(manager_from_ctx(ctx).config_path))


@app.command("show")
def show(ctx: typer.Context) -> None:
    """显示当前配置，不包含 token。"""
    config = manager_from_ctx(ctx).load().model_dump(mode="python")
    print_json(config)
