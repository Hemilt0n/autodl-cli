from __future__ import annotations

from typing import Any

import httpx

from autodl_cli.api.models import Balance, Page
from autodl_cli.constants import API_BASE_URL, DEFAULT_REQUEST_TIMEOUT_SECONDS
from autodl_cli.errors import (
    AutoDLAPIError,
    AutoDLAuthError,
    AutoDLCapacityError,
    AutoDLHTTPError,
)


class AutoDLClient:
    def __init__(
        self,
        *,
        token: str,
        base_url: str = API_BASE_URL,
        timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": token},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AutoDLClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def balance(self) -> Balance:
        return Balance.model_validate(self._request("POST", "/api/v1/dev/wallet/balance"))

    def list_instances(self, *, page_index: int = 1, page_size: int = 20) -> Page:
        data = self._request(
            "POST",
            "/api/v1/dev/instance/pro/list",
            json={"page_index": page_index, "page_size": page_size},
        )
        return _page_from_data(data)

    def instance_status(self, instance_uuid: str) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v1/dev/instance/pro/status",
            params={"instance_uuid": instance_uuid},
        )

    def instance_snapshot(self, instance_uuid: str) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/v1/dev/instance/pro/snapshot",
            params={"instance_uuid": instance_uuid},
        )

    def power_on(self, instance_uuid: str, *, start_command: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"instance_uuid": instance_uuid, "payload": "gpu"}
        if start_command:
            payload["start_command"] = start_command
        return self._request("POST", "/api/v1/dev/instance/pro/power_on", json=payload)

    def power_off(self, instance_uuid: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/dev/instance/pro/power_off",
            json={"instance_uuid": instance_uuid},
        )

    def release(self, instance_uuid: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/dev/instance/pro/release",
            json={"instance_uuid": instance_uuid},
        )

    def save_image(self, instance_uuid: str, image_name: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/dev/instance/pro/image/save",
            json={"instance_uuid": instance_uuid, "image_name": image_name},
        )

    def list_private_images(self, *, page_index: int = 1, page_size: int = 20) -> Page:
        data = self._request(
            "POST",
            "/api/v1/dev/instance/pro/image/private/list",
            json={"page_index": page_index, "page_size": page_size},
        )
        return _page_from_data(data)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.status_code in {401, 403}:
            raise AutoDLAuthError("AutoDL authentication failed.", code=str(response.status_code))
        if response.status_code >= 400:
            raise AutoDLHTTPError(
                f"AutoDL HTTP request failed with status {response.status_code}.",
                status_code=response.status_code,
                body=response.text,
            )

        payload = response.json()
        code = payload.get("code")
        if code != "Success":
            message = str(payload.get("msg") or payload.get("message") or code or "AutoDL API error")
            if _looks_like_auth_error(code, message):
                raise AutoDLAuthError(message, code=code)
            if _looks_like_capacity_error(code, message):
                raise AutoDLCapacityError(message, code=code)
            raise AutoDLAPIError(message, code=code)
        return payload.get("data")


def _page_from_data(data: Any) -> Page:
    if isinstance(data, list):
        return Page(items=data)
    if isinstance(data, dict):
        return Page.model_validate(data)
    return Page()


def _looks_like_auth_error(code: str | None, message: str) -> bool:
    text = f"{code or ''} {message}".lower()
    return any(keyword in text for keyword in ("auth", "token", "unauthorized", "forbidden", "鉴权"))


def _looks_like_capacity_error(code: str | None, message: str) -> bool:
    text = f"{code or ''} {message}".lower()
    return any(keyword in text for keyword in ("capacity", "stock", "resource", "库存", "资源", "无卡"))
