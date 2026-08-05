from fastapi import APIRouter, Response, status

from app.api.dependencies import DatabaseSession, VerifiedWebIntake
from app.models import LeadSource
from app.schemas import WebLeadIntakeRequest, WebLeadIntakeResponse
from app.services import LeadIntakeInput, LeadIntakeService

router = APIRouter(prefix="/intake", tags=["lead intake"])


@router.post(
    "/web",
    response_model=WebLeadIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Accept a signed Web lead",
    description=(
        "Creates or reuses a customer and atomically records a new opportunity. "
        "Requires an HMAC signature from a trusted server integration."
    ),
)
def create_web_lead(
    payload: WebLeadIntakeRequest,
    response: Response,
    session: DatabaseSession,
    _verified_intake: VerifiedWebIntake,
) -> WebLeadIntakeResponse:
    result = LeadIntakeService(session).intake(
        LeadIntakeInput(
            name=payload.name,
            company=payload.company,
            email=payload.email,
            phone=payload.phone,
            province=payload.province,
            message=payload.message,
            source=LeadSource.WEB,
            external_submission_id=payload.external_submission_id,
        )
    )
    response.status_code = (
        status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    )
    return WebLeadIntakeResponse(
        intake_id=result.intake_id,
        customer_id=result.customer_id,
        opportunity_id=result.opportunity_id,
        created=result.created,
    )
