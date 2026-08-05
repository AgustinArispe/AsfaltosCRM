from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import StrictRequestModel
from app.schemas.customer import NonBlankString


class ProductCreate(StrictRequestModel):
    name: NonBlankString


class ProductUpdate(StrictRequestModel):
    name: NonBlankString | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null_fields(self) -> Self:
        for field_name in ("name", "is_active"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
