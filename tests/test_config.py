from __future__ import annotations

import pytest

from autodl_cli.config import ConfigManager, ProfileConfig
from autodl_cli.errors import AutoDLConfigError


def test_config_roundtrip(tmp_path):
    manager = ConfigManager(config_path=tmp_path / "config.toml", data_dir=tmp_path)

    manager.update_profile(
        "default",
        ProfileConfig(
            default_gpu_spec_uuid="gpu-1",
            default_image_uuid="img-1",
            default_data_centers=["dc-1"],
        ),
    )
    loaded = manager.get_profile("default")

    assert loaded.default_gpu_spec_uuid == "gpu-1"
    assert loaded.default_image_uuid == "img-1"
    assert loaded.default_data_centers == ["dc-1"]


def test_file_token_roundtrip(tmp_path):
    manager = ConfigManager(config_path=tmp_path / "config.toml", data_dir=tmp_path)

    manager.set_token("file-test-profile", "secret-token", store="file")

    assert manager.get_token("file-test-profile") == "secret-token"
    assert manager.require_token("file-test-profile") == "secret-token"


def test_auto_token_store_falls_back_to_file_when_keyring_unavailable(tmp_path, monkeypatch):
    manager = ConfigManager(config_path=tmp_path / "config.toml", data_dir=tmp_path)

    def unavailable_keyring(*args):
        raise RuntimeError("No recommended backend was available.")

    monkeypatch.setattr("autodl_cli.config.keyring.set_password", unavailable_keyring)
    monkeypatch.setattr("autodl_cli.config.keyring.get_password", unavailable_keyring)

    actual_store = manager.set_token("linux-profile", "secret-token", store="auto")

    assert actual_store == "file"
    assert manager.get_token("linux-profile") == "secret-token"


def test_explicit_keyring_store_still_errors_when_keyring_unavailable(tmp_path, monkeypatch):
    manager = ConfigManager(config_path=tmp_path / "config.toml", data_dir=tmp_path)

    def unavailable_keyring(*args):
        raise RuntimeError("No recommended backend was available.")

    monkeypatch.setattr("autodl_cli.config.keyring.set_password", unavailable_keyring)

    with pytest.raises(AutoDLConfigError, match="Failed to save token to keyring"):
        manager.set_token("linux-profile", "secret-token", store="keyring")

    assert not (tmp_path / "linux-profile.token").exists()
