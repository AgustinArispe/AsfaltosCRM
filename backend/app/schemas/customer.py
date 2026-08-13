from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.schemas.common import EmailInput, StrictRequestModel

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalNonBlankString = NonBlankString | None


class CustomerCreate(StrictRequestModel):
    name: NonBlankString
    company: OptionalNonBlankString = None
    email: EmailInput | None = None
    phone: OptionalNonBlankString = None
    province: OptionalNonBlankString = None
    legendary_historical_override: bool = False


class CustomerUpdate(StrictRequestModel):
    expected_updated_at: datetime
    name: NonBlankString | None = None
    company: OptionalNonBlankString = None
    email: EmailInput | None = None
    phone: OptionalNonBlankString = None
    province: OptionalNonBlankString = None
    legendary_historical_override: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        if (
            "legendary_historical_override" in self.model_fields_set
            and self.legendary_historical_override is None
        ):
            raise ValueError("legendary_historical_override cannot be null")
        return self


class CustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None
    legendary_historical_override: bool
    legendary_automatic: bool
    legendary_automatic_evaluated_at: datetime | None
    is_legendary: bool
    updated_at: datetime


class CustomerDetail(CustomerSummary):
    created_at: datetime
