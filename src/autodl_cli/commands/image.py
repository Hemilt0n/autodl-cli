from __future__ import annotations

from typing import Any

import typer

from autodl_cli.app import client_from_ctx
from autodl_cli.output import print_json, print_kv, print_rows

app = typer.Typer(help="Pro 镜像相关命令。", no_args_is_help=True)


@app.command("list")
def list_images(
    ctx: typer.Context,
    page_index: int = typer.Option(1, "--page-index", min=1),
    page_size: int = typer.Option(20, "--page-size", min=1, max=100),
) -> None:
    """查看私有 Pro 镜像列表。"""
    with client_from_ctx(ctx) as client:
        page = client.list_private_images(page_index=page_index, page_size=page_size)
    if ctx.obj.json_output:
        print_json(page.model_dump(mode="python"))
    else:
        print_rows("Images", page.items, ["image_uuid", "name", "status", "image_size", "create_at"])


@app.command("save")
def save(ctx: typer.Context, instance_uuid: str, name: str = typer.Option(..., "--name")) -> None:
    """把 Pro 实例保存为私有镜像。"""
    with client_from_ctx(ctx) as client:
        data = client.save_image(instance_uuid, name)
    _print_data(ctx, "Image Save", data)


def _print_data(ctx: typer.Context, title: str, data: Any) -> None:
    if not isinstance(data, dict):
        data = {"result": data}
    if ctx.obj.json_output:
        print_json(data)
    else:
        print_kv(title, data)
