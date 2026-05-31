from __future__ import annotations

from typing import Any

import typer

from autodl_cli.app import client_from_ctx
from autodl_cli.errors import AutoDLError
from autodl_cli.output import print_json, print_kv, print_rows

app = typer.Typer(help="Pro 实例相关命令。", no_args_is_help=True)

_GPU_SPEC_STOCK_NAME_HINTS = {
    "h800": ["h800"],
    "v-48g": ["4090"],
    "v-48g-350w": ["3090"],
    "v-32g-p": ["4080"],
    "v-24g-p": ["3090", "4090"],
    "5090-p": ["5090"],
    "4090d": ["4090d"],
    "pro6000-p": ["pro 6000", "pro6000"],
}


@app.command("list")
def list_instances(
    ctx: typer.Context,
    page_index: int = typer.Option(1, "--page-index", min=1),
    page_size: int = typer.Option(20, "--page-size", min=1, max=100),
    stock: bool = typer.Option(
        False,
        "--stock",
        help="尝试查询企业弹性部署 GPU 库存，并按实例地区/GPU 匹配输出。",
    ),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON，方便脚本处理。"),
) -> None:
    """查看当前账号下的 Pro 实例列表。"""
    with client_from_ctx(ctx) as client:
        page = client.list_instances(page_index=page_index, page_size=page_size)
        rows = [_normalize_instance_summary(row) for row in page.items]
        if stock:
            _attach_stock_status(client, rows)
    if ctx.obj.json_output or json_output:
        print_json(
            {
                "list": rows,
                "page_index": page.page_index,
                "page_size": page.page_size,
                "total_count": page.total_count,
                "total_page": page.total_page,
            }
        )
    else:
        columns = ["uuid", "name", "status", "gpu_spec_uuid", "gpu_amount"]
        if stock:
            columns.append("stock")
        print_rows(
            "实例列表",
            rows,
            columns,
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
    normalized["region_sign"] = _first_present(
        row,
        "region_sign",
        "data_center",
        "data_center_sign",
        "region",
    )
    normalized["gpu_name"] = _first_present(
        row,
        "gpu_name",
        "gpu_model",
        "gpu_type",
        "gpu_spec_name",
    )
    return normalized


def _attach_stock_status(client: Any, rows: list[dict[str, Any]]) -> None:
    stock_by_region: dict[str, dict[str, dict[str, Any]] | str] = {}
    for row in rows:
        region_sign = str(row.get("region_sign") or "")
        if not region_sign:
            _mark_stock_unknown(row, "missing region_sign")
            continue
        if region_sign not in stock_by_region:
            try:
                stock_by_region[region_sign] = _index_stock_items(client.gpu_stock(region_sign=region_sign))
            except AutoDLError as exc:
                stock_by_region[region_sign] = str(exc)

        stock_index = stock_by_region[region_sign]
        if isinstance(stock_index, str):
            _mark_stock_unknown(row, stock_index)
            continue

        stock_name, stock_item = _match_stock_item(row, stock_index)
        if not stock_item:
            _mark_stock_unknown(row, "no matching gpu stock")
            continue
        _apply_stock_item(row, stock_name, stock_item)


def _index_stock_items(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        for gpu_name, stock_item in item.items():
            if isinstance(stock_item, dict):
                indexed[str(gpu_name)] = stock_item
    return indexed


def _match_stock_item(
    row: dict[str, Any],
    stock_index: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    hints = _stock_name_hints(row)
    for stock_name, stock_item in stock_index.items():
        normalized_stock_name = stock_name.lower()
        if any(hint in normalized_stock_name for hint in hints):
            return stock_name, stock_item
    return "", None


def _stock_name_hints(row: dict[str, Any]) -> list[str]:
    gpu_name = str(row.get("gpu_name") or "").strip().lower()
    if gpu_name:
        return [gpu_name]
    gpu_spec_uuid = str(row.get("gpu_spec_uuid") or "").strip().lower()
    return _GPU_SPEC_STOCK_NAME_HINTS.get(gpu_spec_uuid, [gpu_spec_uuid] if gpu_spec_uuid else [])


def _apply_stock_item(row: dict[str, Any], stock_name: str, stock_item: dict[str, Any]) -> None:
    idle_gpu_num = _stock_number(stock_item, "idle_gpu_num", "idle_gpu")
    total_gpu_num = _stock_number(stock_item, "total_gpu_num", "total_gpu")
    required_gpu_num = _int_or_zero(row.get("gpu_amount"))
    row["stock_region"] = row.get("region_sign") or ""
    row["stock_gpu_name"] = stock_name
    row["stock_idle_gpu_num"] = idle_gpu_num
    row["stock_total_gpu_num"] = total_gpu_num
    row["stock_status"] = "available" if idle_gpu_num >= max(required_gpu_num, 1) else "no_stock"
    row["stock"] = f"{idle_gpu_num}/{total_gpu_num}" if total_gpu_num else str(idle_gpu_num)


def _mark_stock_unknown(row: dict[str, Any], reason: str) -> None:
    row["stock_status"] = "unknown"
    row["stock_error"] = reason
    row["stock"] = "unknown"


def _stock_number(stock_item: dict[str, Any], *keys: str) -> int:
    return _int_or_zero(_first_present(stock_item, *keys))


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
