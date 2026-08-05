from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import UserRole
from app.schemas.auth import PasswordInput
from app.schemas.common import EmailInput, StrictRequestModel
from app.schemas.customer import NonBlankString


class UserCreate(StrictRequestModel):
    full_name: NonBlankString
    email: EmailInput
    password: PasswordInput
    role: UserRole


class UserUpdate(StrictRequestModel):
    full_name: NonBlankString | None = None
    email: EmailInput | None = None
    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null_fields(self) -> Self:
        for field_name in ("full_name", "email", "role", "is_active"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PasswordUpdate(StrictRequestModel):
    password: PasswordInput


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
