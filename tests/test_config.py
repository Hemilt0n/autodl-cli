from __future__ import annotations

from autodl_cli.config import ConfigManager, ProfileConfig


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
