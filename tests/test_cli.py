from __future__ import annotations

import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from autodl_cli.app import app

runner = CliRunner()


def test_account_balance_command(tmp_path: Path):
    config_path = tmp_path / "config.toml"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/dev/wallet/balance"
        return httpx.Response(
            200,
            json={"code": "Success", "data": {"assets": 1000, "voucher_balance": 0, "accumulate": 0}},
        )

    with _mock_client(handler):
        result = runner.invoke(
            app,
            ["--config", str(config_path), "--token", "token-1", "--json", "account", "balance"],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["cash_yuan"] == 1


def test_instance_list_command(tmp_path: Path):
    config_path = tmp_path / "config.toml"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/dev/instance/pro/list"
        return httpx.Response(
            200,
            json={
                "code": "Success",
                "data": {"list": [{"instance_uuid": "i-1", "status": "running"}]},
            },
        )

    with _mock_client(handler):
        result = runner.invoke(
            app,
            ["--config", str(config_path), "--token", "token-1", "--json", "instance", "list"],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["list"][0]["instance_uuid"] == "i-1"


def test_instance_list_table_uses_documented_uuid_and_name(tmp_path: Path):
    config_path = tmp_path / "config.toml"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/dev/instance/pro/list"
        return httpx.Response(
            200,
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {
                            "uuid": "pro-abc",
                            "name": "train-job",
                            "status": "running",
                            "gpu_spec_uuid": "4090",
                            "gpu_amount": 1,
                        }
                    ]
                },
            },
        )

    with _mock_client(handler):
        result = runner.invoke(
            app,
            ["--config", str(config_path), "--token", "token-1", "instance", "list"],
        )

    assert result.exit_code == 0
    assert "pro-abc" in result.stdout
    assert "train-job" in result.stdout


def test_help_is_chinese_by_default():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "AutoDL Pro 命令行工具" in result.stdout
    assert "账户相关命令" in result.stdout
    assert "create" not in result.stdout


def test_image_save_command(tmp_path: Path):
    config_path = tmp_path / "config.toml"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/dev/instance/pro/image/save"
        payload = json.loads(request.content)
        assert payload == {"instance_uuid": "i-1", "image_name": "snapshot"}
        return httpx.Response(200, json={"code": "Success", "data": {"image_uuid": "img-1"}})

    with _mock_client(handler):
        result = runner.invoke(
            app,
            [
                "--config",
                str(config_path),
                "--token",
                "token-1",
                "--json",
                "image",
                "save",
                "i-1",
                "--name",
                "snapshot",
            ],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["image_uuid"] == "img-1"


def test_instance_destroy_stops_then_releases(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"code": "Success", "data": {}})

    with _mock_client(handler):
        result = runner.invoke(
            app,
            [
                "--config",
                str(config_path),
                "--token",
                "token-1",
                "--json",
                "instance",
                "destroy",
                "i-1",
                "--yes",
            ],
        )

    assert result.exit_code == 0
    assert paths == [
        "/api/v1/dev/instance/pro/power_off",
        "/api/v1/dev/instance/pro/release",
    ]


def test_version_command():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "autodl-cli 0.1.0" in result.stdout


class _mock_client:
    def __init__(self, handler):
        self.handler = handler
        self.original_init = None

    def __enter__(self):
        from autodl_cli.api.client import AutoDLClient

        self.original_init = AutoDLClient.__init__

        def init(instance, *, token, base_url="https://api.autodl.com", timeout=30.0, transport=None):
            self.original_init(
                instance,
                token=token,
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(self.handler),
            )

        AutoDLClient.__init__ = init
        return self

    def __exit__(self, *_exc):
        from autodl_cli.api.client import AutoDLClient

        AutoDLClient.__init__ = self.original_init
