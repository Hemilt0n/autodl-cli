from __future__ import annotations

import json

import httpx
import pytest

from autodl_cli.api.client import AutoDLClient
from autodl_cli.api.models import InstanceCreateRequest
from autodl_cli.errors import AutoDLAPIError, AutoDLCapacityError


def test_balance_parses_yuan():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "token-1"
        assert request.url.path == "/api/v1/dev/wallet/balance"
        return httpx.Response(
            200,
            json={
                "code": "Success",
                "data": {"assets": 12345, "voucher_balance": 2000, "accumulate": 3000},
            },
        )

    client = AutoDLClient(token="token-1", transport=httpx.MockTransport(handler))

    balance = client.balance()

    assert balance.cash_yuan == 12.345
    assert balance.voucher_yuan == 2
    assert balance.spent_yuan == 3


def test_create_instance_payload_omits_empty_data_centers():
    seen_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_payload
        seen_payload = dict(json.loads(request.content))
        return httpx.Response(200, json={"code": "Success", "data": {"instance_uuid": "i-1"}})

    client = AutoDLClient(token="token-1", transport=httpx.MockTransport(handler))

    data = client.create_instance(
        InstanceCreateRequest(gpu_spec_uuid="gpu", image_uuid="img", cuda_v_from=118)
    )

    assert data == {"instance_uuid": "i-1"}
    assert "data_center_list" not in seen_payload
    assert seen_payload["gpu_spec_uuid"] == "gpu"


def test_capacity_error_classification():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "NoStock", "msg": "库存不足"})

    client = AutoDLClient(token="token-1", transport=httpx.MockTransport(handler))

    with pytest.raises(AutoDLCapacityError):
        client.power_on("i-1")


def test_api_error_classification():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "BadRequest", "msg": "bad request"})

    client = AutoDLClient(token="token-1", transport=httpx.MockTransport(handler))

    with pytest.raises(AutoDLAPIError):
        client.balance()
