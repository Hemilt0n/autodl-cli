from __future__ import annotations

import typer

from autodl_cli.app import client_from_ctx
from autodl_cli.output import print_json, print_kv

app = typer.Typer(help="Authentication helpers.", no_args_is_help=True)


@app.command("check")
def check(ctx: typer.Context) -> None:
    """Validate the configured token using the balance endpoint."""
    with client_from_ctx(ctx) as client:
        balance = client.balance()
    if ctx.obj.json_output:
        print_json({"ok": True})
    else:
        print_kv("Auth", {"ok": True, "cash_yuan": f"{balance.cash_yuan:.3f}"})
