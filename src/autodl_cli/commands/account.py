from __future__ import annotations

import typer

from autodl_cli.app import client_from_ctx
from autodl_cli.output import print_json, print_kv

app = typer.Typer(help="账户相关命令。", no_args_is_help=True)


@app.command("balance")
def balance(ctx: typer.Context) -> None:
    """查看账户余额。"""
    with client_from_ctx(ctx) as client:
        result = client.balance()

    data = {
        "cash_yuan": result.cash_yuan,
        "voucher_yuan": result.voucher_yuan,
        "spent_yuan": result.spent_yuan,
    }
    if ctx.obj.json_output:
        print_json(data)
    else:
        print_kv(
            "Balance",
            {
                "cash": f"{result.cash_yuan:.3f} CNY",
                "voucher": f"{result.voucher_yuan:.3f} CNY",
                "spent": f"{result.spent_yuan:.3f} CNY",
            },
        )
