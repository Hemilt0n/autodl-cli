from __future__ import annotations

from pathlib import Path

import typer

from autodl_cli.app import client_from_ctx, manager_from_ctx
from autodl_cli.output import print_json, print_kv

app = typer.Typer(help="认证相关命令。", no_args_is_help=True)


@app.command("web-token")
def web_token(
    ctx: typer.Context,
    token_file: Path | None = typer.Option(
        None, "--token-file", exists=True, dir_okay=False, readable=True,
        help="从文件导入网页登录 Token；未指定时隐藏输入。",
    ),
    token_store: str = typer.Option("auto", "--token-store", help="auto、keyring 或 file。"),
) -> None:
    """配置当前 profile 的网页登录 Token，与开发者 Token 分开保存。"""
    if token_store not in {"auto", "keyring", "file"}:
        raise typer.BadParameter("请选择 auto、keyring 或 file。", param_hint="--token-store")
    token = token_file.read_text().strip() if token_file else typer.prompt(
        "网页登录 Token", hide_input=True
    ).strip()
    store = manager_from_ctx(ctx).set_token(ctx.obj.profile, token, store=token_store, web=True)
    if ctx.obj.json_output:
        print_json({"ok": True, "store": store})
    else:
        print_kv("网页登录 Token 已保存", {"profile": ctx.obj.profile, "store": store})


@app.command("check")
def check(ctx: typer.Context) -> None:
    """检查当前 token 是否可用。"""
    with client_from_ctx(ctx) as client:
        balance = client.balance()
    if ctx.obj.json_output:
        print_json({"ok": True})
    else:
        print_kv("Auth", {"ok": True, "cash_yuan": f"{balance.cash_yuan:.3f}"})
