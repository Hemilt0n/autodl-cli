from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True, serialize_by_alias=True)


class Balance(FlexibleModel):
    assets: int = 0
    accumulate: int = 0
    voucher_balance: int = 0

    @property
    def cash_yuan(self) -> float:
        return self.assets / 1000

    @property
    def spent_yuan(self) -> float:
        return self.accumulate / 1000

    @property
    def voucher_yuan(self) -> float:
        return self.voucher_balance / 1000


class Page(FlexibleModel):
    items: list[dict[str, Any]] = Field(default_factory=list, alias="list")
    page_index: int | None = None
    page_size: int | None = None
    total_count: int | None = None
    total_page: int | None = None


class InstanceCreateRequest(FlexibleModel):
    gpu_spec_uuid: str
    image_uuid: str
    cuda_v_from: int
    req_gpu_amount: int = 1
    expand_system_disk_by_gb: int = 0
    data_center_list: list[str] = Field(default_factory=list)
    instance_name: str | None = None
    start_command: str | None = None

    def payload(self) -> dict[str, Any]:
        data = self.model_dump(exclude_none=True)
        if not data["data_center_list"]:
            data.pop("data_center_list")
        return data
