from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.common import EmailInput, StrictRequestModel

ExternalSubmissionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
LeadName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
OptionalCompany = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    ]
    | None
)
OptionalPhone = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    | None
)
OptionalProvince = (
    Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    | None
)
OptionalMessage = (
    Annotated[
        str,
        StringConstraints(max_length=10_000),
    ]
    | None
)


class WebLeadIntakeRequest(StrictRequestModel):
    external_submission_id: ExternalSubmissionId
    name: LeadName
    company: OptionalCompany = None
    email: EmailInput | None = None
    phone: OptionalPhone = None
    province: OptionalProvince = None
    message: OptionalMessage = None


class WebLeadIntakeResponse(BaseModel):
    intake_id: int
    customer_id: int
    opportunity_id: int
    created: bool
