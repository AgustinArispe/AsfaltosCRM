from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


ResponseItem = TypeVar("ResponseItem")


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaginatedResponse(BaseModel, Generic[ResponseItem]):
    items: list[ResponseItem]
    page: int
    page_size: int
    total: int
