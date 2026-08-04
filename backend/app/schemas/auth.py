from typing import Annotated, Literal

from pydantic import Field, SecretStr, StringConstraints

from app.schemas.common import StrictRequestModel


EmailInput = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=320),
]
PasswordInput = Annotated[SecretStr, Field(min_length=8, max_length=128)]
LoginPasswordInput = Annotated[SecretStr, Field(min_length=1, max_length=128)]


class LoginRequest(StrictRequestModel):
    email: EmailInput
    password: LoginPasswordInput


class TokenResponse(StrictRequestModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
