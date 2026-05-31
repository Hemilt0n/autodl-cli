from __future__ import annotations

from typing import Any

import typer

from autodl_cli.api.models import InstanceCreateRequest
from autodl_cli.app import client_from_ctx, manager_from_ctx
from autodl_cli.errors import AutoDLConfigError
from autodl_cli.output import print_json, print_kv, print_rows

app = typer.Typer(help="Pro instance commands.", no_args_is_help=True)


@app.command("list")
def list_instances(
    ctx: typer.Context,
    page_index: int = typer.Option(1, "--page-index", min=1),
    page_size: int = typer.Option(20, "--page-size", min=1, max=100),
) -> None:
    """List Pro instances for the current account."""
    with client_from_ctx(ctx) as client:
        page = client.list_instances(page_index=page_index, page_size=page_size)
    rows = page.items
    if ctx.obj.json_output:
        print_json(page.model_dump(mode="python"))
    else:
        print_rows(
            "Instances",
            rows,
            ["instance_uuid", "instance_name", "status", "gpu_spec_uuid", "req_gpu_amount"],
        )


@app.command("status")
def status(ctx: typer.Context, instance_uuid: str) -> None:
    """Show a Pro instance status."""
    with client_from_ctx(ctx) as client:
        data = client.instance_status(instance_uuid)
    _print_data(ctx, "Instance Status", data)


@app.command("inspect")
def inspect(ctx: typer.Context, instance_uuid: str) -> None:
    """Show a Pro instance snapshot. Secrets are redacted by default."""
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
    """Create a Pro instance. This is a billable API operation."""
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
    """Power on a Pro instance in GPU mode."""
    with client_from_ctx(ctx) as client:
        data = client.power_on(instance_uuid, start_command=start_command)
    _print_data(ctx, "Instance Start", data or {"ok": True})


@app.command("stop")
def stop(ctx: typer.Context, instance_uuid: str) -> None:
    """Power off a Pro instance."""
    with client_from_ctx(ctx) as client:
        data = client.power_off(instance_uuid)
    _print_data(ctx, "Instance Stop", data or {"ok": True})


@app.command("release")
def release(
    ctx: typer.Context,
    instance_uuid: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Release a stopped Pro instance."""
    if not yes:
        typer.confirm(f"Release instance {instance_uuid}?", abort=True)
    with client_from_ctx(ctx) as client:
        data = client.release(instance_uuid)
    _print_data(ctx, "Instance Release", data or {"ok": True})


@app.command("destroy")
def destroy(
    ctx: typer.Context,
    instance_uuid: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Power off and then release a Pro instance."""
    if not yes:
        typer.confirm(f"Power off and release instance {instance_uuid}?", abort=True)
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


def _print_data(ctx: typer.Context, title: str, data: Any) -> None:
    if not isinstance(data, dict):
        data = {"result": data}
    if ctx.obj.json_output:
        print_json(data)
    else:
        print_kv(title, data)
