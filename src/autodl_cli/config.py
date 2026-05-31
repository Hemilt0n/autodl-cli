from __future__ import annotations

import contextlib
import os
import tomllib
from pathlib import Path
from typing import Any

import keyring
import tomli_w
from platformdirs import user_config_dir, user_data_dir
from pydantic import BaseModel, Field

from autodl_cli.constants import API_BASE_URL, APP_NAME, CONFIG_FILE_NAME
from autodl_cli.errors import AutoDLConfigError

_KEYRING_SERVICE = APP_NAME


class ProfileConfig(BaseModel):
    base_url: str = API_BASE_URL
    default_data_centers: list[str] = Field(default_factory=list)
    default_gpu_spec_uuid: str = ""
    default_gpu_amount: int = 1
    default_image_uuid: str = ""
    default_cuda_v_from: int = 118
    default_expand_system_disk_by_gb: int = 0
    min_balance_yuan: float = 0.0


class AppConfig(BaseModel):
    profiles: dict[str, ProfileConfig] = Field(
        default_factory=lambda: {"default": ProfileConfig()}
    )


class ConfigManager:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        config_dir: Path | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self._config_path = config_path
        self._config_dir = config_dir or Path(user_config_dir(APP_NAME))
        self._data_dir = data_dir or Path(user_data_dir(APP_NAME))

    @property
    def config_path(self) -> Path:
        return self._config_path or self._config_dir / CONFIG_FILE_NAME

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def load(self) -> AppConfig:
        path = self.config_path
        if not path.exists():
            return AppConfig()

        data = tomllib.loads(path.read_text(encoding="utf-8"))
        raw_profiles: dict[str, Any] = data.get("profile", data.get("profiles", {}))
        if not raw_profiles:
            return AppConfig()
        return AppConfig(
            profiles={
                name: ProfileConfig.model_validate(profile)
                for name, profile in raw_profiles.items()
            }
        )

    def save(self, config: AppConfig) -> None:
        path = self.config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "profile": {
                name: profile.model_dump(mode="python")
                for name, profile in config.profiles.items()
            }
        }
        path.write_text(tomli_w.dumps(payload), encoding="utf-8")
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)

    def get_profile(self, name: str) -> ProfileConfig:
        config = self.load()
        return config.profiles.get(name, ProfileConfig())

    def update_profile(self, name: str, profile: ProfileConfig) -> None:
        config = self.load()
        config.profiles[name] = profile
        self.save(config)

    def get_token(self, profile: str) -> str | None:
        with contextlib.suppress(Exception):
            token = keyring.get_password(_KEYRING_SERVICE, profile)
            if token:
                return token

        token_path = self._token_path(profile)
        if token_path.exists():
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        return None

    def set_token(self, profile: str, token: str, *, store: str = "keyring") -> None:
        if not token.strip():
            raise AutoDLConfigError("Token cannot be empty.")

        if store == "keyring":
            try:
                keyring.set_password(_KEYRING_SERVICE, profile, token)
            except Exception as exc:
                raise AutoDLConfigError(
                    "Failed to save token to keyring. Use --token-store file if needed."
                ) from exc
            token_path = self._token_path(profile)
            if token_path.exists():
                token_path.unlink()
            return

        if store == "file":
            with contextlib.suppress(Exception):
                keyring.delete_password(_KEYRING_SERVICE, profile)
            self._data_dir.mkdir(parents=True, exist_ok=True)
            token_path = self._token_path(profile)
            token_path.write_text(token, encoding="utf-8")
            with contextlib.suppress(OSError):
                os.chmod(token_path, 0o600)
            return

        raise AutoDLConfigError("Token store must be 'keyring' or 'file'.")

    def require_token(self, profile: str, override: str = "") -> str:
        if override:
            return override
        token = self.get_token(profile)
        if token:
            return token
        raise AutoDLConfigError(
            f"No token configured for profile '{profile}'. Run `autodl init` first."
        )

    def _token_path(self, profile: str) -> Path:
        return self._data_dir / f"{profile}.token"
