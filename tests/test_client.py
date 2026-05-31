from __future__ import annotations

import httpx
import pytest

from autodl_cli.api.client import AutoDLClient
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
