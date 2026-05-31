from __future__ import annotations

from typing import Any

import typer

from autodl_cli.app import client_from_ctx
from autodl_cli.output import print_json, print_kv, print_rows

app = typer.Typer(help="Pro 实例相关命令。", no_args_is_help=True)


@app.command("list")
def list_instances(
    ctx: typer.Context,
    page_index: int = typer.Option(1, "--page-index", min=1),
    page_size: int = typer.Option(20, "--page-size", min=1, max=100),
) -> None:
    """查看当前账号下的 Pro 实例列表。"""
    with client_from_ctx(ctx) as client:
        page = client.list_instances(page_index=page_index, page_size=page_size)
    rows = [_normalize_instance_summary(row) for row in page.items]
    if ctx.obj.json_output:
        print_json(page.model_dump(mode="python"))
    else:
        print_rows(
            "实例列表",
            rows,
            ["uuid", "name", "status", "gpu_spec_uuid", "gpu_amount"],
        )


@app.command("status")
def status(ctx: typer.Context, instance_uuid: str) -> None:
    """查看 Pro 实例状态。"""
    with client_from_ctx(ctx) as client:
        data = client.instance_status(instance_uuid)
    _print_data(ctx, "Instance Status", data)


@app.command("inspect")
def inspect(ctx: typer.Context, instance_uuid: str) -> None:
    """查看 Pro 实例详情，默认隐藏敏感信息。"""
    with client_from_ctx(ctx) as client:
        data = client.instance_snapshot(instance_uuid)
    _print_data(ctx, "Instance", data)


@app.command("start")
def start(
    ctx: typer.Context,
    instance_uuid: str,
    start_command: str | None = typer.Option(None, "--start-command"),
) -> None:
    """以有卡模式开机 Pro 实例。"""
    with client_from_ctx(ctx) as client:
        data = client.power_on(instance_uuid, start_command=start_command)
    _print_data(ctx, "Instance Start", data or {"ok": True})


@app.command("stop")
def stop(ctx: typer.Context, instance_uuid: str) -> None:
    """关机 Pro 实例。"""
    with client_from_ctx(ctx) as client:
        data = client.power_off(instance_uuid)
    _print_data(ctx, "Instance Stop", data or {"ok": True})


@app.command("release")
def release(
    ctx: typer.Context,
    instance_uuid: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认。"),
) -> None:
    """释放已关机的 Pro 实例。"""
    _warn_dangerous_operation(
        "高危操作：release 会释放实例资源。请确认实例内重要数据、镜像和任务状态已经处理完毕。",
        instance_uuid,
    )
    if not yes:
        typer.confirm(f"确认继续释放实例 {instance_uuid}？", abort=True)
    with client_from_ctx(ctx) as client:
        data = client.release(instance_uuid)
    _print_data(ctx, "Instance Release", data or {"ok": True})


@app.command("destroy")
def destroy(
    ctx: typer.Context,
    instance_uuid: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认。"),
) -> None:
    """先关机再释放 Pro 实例。"""
    _warn_dangerous_operation(
        "高危操作：destroy 会先关机再释放实例资源。请确认实例内重要数据、镜像和任务状态已经处理完毕。",
        instance_uuid,
    )
    if not yes:
        typer.confirm(f"确认继续关机并释放实例 {instance_uuid}？", abort=True)
    with client_from_ctx(ctx) as client:
        stop_result = client.power_off(instance_uuid)
        release_result = client.release(instance_uuid)
    _print_data(
        ctx,
        "Instance Destroy",
        {"stopped": stop_result or True, "released": release_result or True},
    )


def _normalize_instance_summary(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize documented and legacy field names for table output."""
    normalized = dict(row)
    normalized["uuid"] = _first_present(
        row,
        "uuid",
        "instance_uuid",
        "id",
    )
    normalized["name"] = _first_present(
        row,
        "name",
        "instance_name",
        "remark",
    )
    normalized["gpu_amount"] = _first_present(
        row,
        "gpu_amount",
        "req_gpu_amount",
        "gpu_num",
    )
    return normalized


def _first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def _warn_dangerous_operation(message: str, instance_uuid: str) -> None:
    typer.secho("!!! 高危操作警告 !!!", fg=typer.colors.RED, bold=True, err=True)
    typer.secho(message, fg=typer.colors.RED, err=True)
    typer.secho(f"目标实例：{instance_uuid}", fg=typer.colors.RED, err=True)


def _print_data(ctx: typer.Context, title: str, data: Any) -> None:
    if not isinstance(data, dict):
        data = {"result": data}
    if ctx.obj.json_output:
        print_json(data)
    else:
        print_kv(title, data)
