from __future__ import annotations

import typer

from autodl_cli.app import manager_from_ctx
from autodl_cli.config import ProfileConfig


def init_command(
    ctx: typer.Context,
    token: str = typer.Option("", "--token", "-T", prompt=True, hide_input=True),
    token_store: str = typer.Option("keyring", "--token-store", help="keyring or file."),
    gpu_spec_uuid: str = typer.Option("", "--gpu-spec-uuid"),
    image_uuid: str = typer.Option("", "--image-uuid"),
    cuda_v_from: int = typer.Option(118, "--cuda-v-from"),
    gpu_amount: int = typer.Option(1, "--gpu-amount"),
    disk_gb: int = typer.Option(0, "--disk-gb"),
    data_center: list[str] | None = typer.Option(None, "--data-center"),
) -> None:
    """Initialize a profile with token and default Pro instance options."""
    manager = manager_from_ctx(ctx)
    manager.set_token(ctx.obj.profile, token, store=token_store)
    existing = manager.get_profile(ctx.obj.profile)
    manager.update_profile(
        ctx.obj.profile,
        ProfileConfig(
            base_url=ctx.obj.base_url or existing.base_url,
            default_data_centers=data_center or existing.default_data_centers,
            default_gpu_spec_uuid=gpu_spec_uuid or existing.default_gpu_spec_uuid,
            default_gpu_amount=gpu_amount,
            default_image_uuid=image_uuid or existing.default_image_uuid,
            default_cuda_v_from=cuda_v_from,
            default_expand_system_disk_by_gb=disk_gb,
            min_balance_yuan=existing.min_balance_yuan,
        ),
    )
    typer.echo(f"Profile '{ctx.obj.profile}' saved: {manager.config_path}")
