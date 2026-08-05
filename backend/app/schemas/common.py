from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints


ResponseItem = TypeVar("ResponseItem")


def validate_email_format(value: str) -> str:
    """Reject obviously malformed addresses without imposing deliverability rules."""
    if value.count("@") != 1 or any(character.isspace() for character in value):
        raise ValueError("value is not a valid email address")
    local_part, domain = value.split("@")
    if (
        not local_part
        or not domain
        or len(local_part) > 64
        or len(domain) > 255
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or domain.startswith(".")
        or domain.endswith(".")
        or ".." in domain
    ):
        raise ValueError("value is not a valid email address")
    return value


EmailInput = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=320),
    AfterValidator(validate_email_format),
]


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaginatedResponse(BaseModel, Generic[ResponseItem]):
    items: list[ResponseItem]
    page: int
    page_size: int
    total: int
