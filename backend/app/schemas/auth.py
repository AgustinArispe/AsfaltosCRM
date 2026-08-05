from typing import Annotated, Literal

from pydantic import Field, SecretStr

from app.schemas.common import EmailInput, StrictRequestModel

PasswordInput = Annotated[SecretStr, Field(min_length=8, max_length=128)]
LoginPasswordInput = Annotated[SecretStr, Field(min_length=1, max_length=128)]


class LoginRequest(StrictRequestModel):
    email: EmailInput
    password: LoginPasswordInput


class TokenResponse(StrictRequestModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
