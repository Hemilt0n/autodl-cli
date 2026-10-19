from __future__ import annotations

from typing import Any

from autodl_cli.api.client import AutoDLClient
from autodl_cli.errors import AutoDLAuthError


class AutoDLWebClient(AutoDLClient):
    """Web session authentication for the console's non-GPU start endpoint."""

    def __init__(self, *, token: str) -> None:
        super().__init__(token=token, base_url="https://www.autodl.com")
        self._client.headers["AppVersion"] = "0.0.0"

    def power_on_no_gpu(self, instance_uuid: str) -> Any:
        try:
            return self._request(
                "POST", "/api/v1/instance/pro/power_on",
                json={"instance_uuid": instance_uuid, "payload": "non_gpu"},
            )
        except AutoDLAuthError as exc:
            raise AutoDLAuthError(
                "网页登录 Token 已失效，请运行 `autodl auth web-token` 更新。",
                code=exc.code,
            ) from None
