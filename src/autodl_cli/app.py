from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from autodl_cli.api import AutoDLClient
from autodl_cli.config import ConfigManager
from autodl_cli.constants import API_BASE_URL
from autodl_cli.errors import AutoDLError


@dataclass
class AppContext:
    profile: str
    config_path: Path | None
    base_url: str | None
    token: str
    json_output: bool


app = typer.Typer(
    name="autodl",
    help="AutoDL Pro 命令行工具。",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)


@app.callback()
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="显示版本并退出。",
        is_eager=True,
    ),
    profile: str = typer.Option("default", "--profile", "-P", help="配置 profile 名称。"),
    config: Path | None = typer.Option(None, "--config", "-C", help="指定配置文件路径。"),
    base_url: str | None = typer.Option(None, "--base-url", help="覆盖 AutoDL API 地址。"),
    token: str = typer.Option("", "--token", "-T", help="临时 token，不写入配置。"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON，方便脚本处理。"),
) -> None:
    if version:
        typer.echo("autodl-cli 0.1.0")
        raise typer.Exit
    ctx.obj = AppContext(profile, config, base_url, token, json_output)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


def manager_from_ctx(ctx: typer.Context) -> ConfigManager:
    obj = _ctx(ctx)
    return ConfigManager(config_path=obj.config_path)


def client_from_ctx(ctx: typer.Context) -> AutoDLClient:
    obj = _ctx(ctx)
    manager = manager_from_ctx(ctx)
    profile = manager.get_profile(obj.profile)
    token = manager.require_token(obj.profile, obj.token)
    return AutoDLClient(token=token, base_url=obj.base_url or profile.base_url or API_BASE_URL)


def _ctx(ctx: typer.Context) -> AppContext:
    if not isinstance(ctx.obj, AppContext):
        raise RuntimeError("Missing Typer context.")
    return ctx.obj


def _run() -> int:
    try:
        app()
    except AutoDLError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        return 1
    return 0


from autodl_cli.commands import account, auth, config, image, init, instance  # noqa: E402

app.add_typer(auth.app, name="auth")
app.add_typer(account.app, name="account")
app.add_typer(config.app, name="config")
app.add_typer(instance.app, name="instance")
app.add_typer(image.app, name="image")
app.command(name="init")(init.init_command)


def main() -> int:
    return _run()
