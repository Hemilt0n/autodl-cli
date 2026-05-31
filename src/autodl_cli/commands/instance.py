from __future__ import annotations

from typing import Any

import typer

from autodl_cli.api.models import InstanceCreateRequest
from autodl_cli.app import client_from_ctx, manager_from_ctx
from autodl_cli.errors import AutoDLConfigError
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


@app.command("create")
def create(
    ctx: typer.Context,
    gpu_spec_uuid: str = typer.Option("", "--gpu-spec-uuid"),
    image_uuid: str = typer.Option("", "--image-uuid"),
    cuda_v_from: int | None = typer.Option(None, "--cuda-v-from"),
    gpu_amount: int | None = typer.Option(None, "--gpu-amount", min=1, max=4),
    disk_gb: int | None = typer.Option(None, "--disk-gb", min=0, max=500),
    data_center: list[str] | None = typer.Option(None, "--data-center"),
    name: str | None = typer.Option(None, "--name"),
    start_command: str | None = typer.Option(None, "--start-command"),
) -> None:
    """创建 Pro 实例。注意：这是可能产生费用的操作。"""
    profile = manager_from_ctx(ctx).get_profile(ctx.obj.profile)
    request = InstanceCreateRequest(
        gpu_spec_uuid=gpu_spec_uuid or _required_default(profile.default_gpu_spec_uuid, "gpu_spec_uuid"),
        image_uuid=image_uuid or _required_default(profile.default_image_uuid, "image_uuid"),
        cuda_v_from=cuda_v_from or profile.default_cuda_v_from,
        req_gpu_amount=gpu_amount or profile.default_gpu_amount,
        expand_system_disk_by_gb=(
            profile.default_expand_system_disk_by_gb if disk_gb is None else disk_gb
        ),
        data_center_list=data_center or profile.default_data_centers,
        instance_name=name,
        start_command=start_command,
    )
    with client_from_ctx(ctx) as client:
        data = client.create_instance(request)
    _print_data(ctx, "Instance Created", data)


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
    if not yes:
        typer.confirm(f"确定释放实例 {instance_uuid} 吗？", abort=True)
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
    if not yes:
        typer.confirm(f"确定关机并释放实例 {instance_uuid} 吗？", abort=True)
    with client_from_ctx(ctx) as client:
        stop_result = client.power_off(instance_uuid)
        release_result = client.release(instance_uuid)
    _print_data(
        ctx,
        "Instance Destroy",
        {"stopped": stop_result or True, "released": release_result or True},
    )


def _required_default(value: str, name: str) -> str:
    if value:
        return value
    raise AutoDLConfigError(f"Missing {name}. Pass it explicitly or run `autodl init`.")


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


def _print_data(ctx: typer.Context, title: str, data: Any) -> None:
    if not isinstance(data, dict):
        data = {"result": data}
    if ctx.obj.json_output:
        print_json(data)
    else:
        print_kv(title, data)
