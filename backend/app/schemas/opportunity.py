from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models import (
    LeadSource,
    LossReason,
    OpportunityStatus,
    OpportunityTransitionKind,
)
from app.schemas.common import EmailInput, StrictRequestModel
from app.schemas.customer import CustomerSummary, NonBlankString, OptionalNonBlankString
from app.schemas.product import ProductResponse

PositiveId = Annotated[int, Field(gt=0)]
PositiveQuantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=14, decimal_places=3),
]
LossReasonDetail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class OpportunityCreate(StrictRequestModel):
    customer_id: PositiveId
    source: Literal[LeadSource.REFERIDO]
    assigned_user_id: PositiveId | None = None


class ExistingCustomerForManualOpportunity(StrictRequestModel):
    kind: Literal["existing"]
    customer_id: PositiveId


class NewCustomerForManualOpportunity(StrictRequestModel):
    kind: Literal["new"]
    name: NonBlankString
    company: OptionalNonBlankString = None
    phone: OptionalNonBlankString = None
    email: EmailInput | None = None
    province: OptionalNonBlankString = None

    @field_validator("company", "phone", "email", "province", mode="before")
    @classmethod
    def normalize_optional_blanks(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


ManualOpportunityCustomer = Annotated[
    ExistingCustomerForManualOpportunity | NewCustomerForManualOpportunity,
    Field(discriminator="kind"),
]


class ManualOpportunityCreate(StrictRequestModel):
    command_id: UUID
    assigned_user_id: PositiveId | None = None
    customer: ManualOpportunityCustomer


class QuoteProductRequest(StrictRequestModel):
    product_id: PositiveId
    quantity_kg: PositiveQuantity


class QuoteRequest(StrictRequestModel):
    products: list[QuoteProductRequest] = Field(min_length=1)


class QuoteProductsUpdate(StrictRequestModel):
    expected_updated_at: datetime
    products: list[QuoteProductRequest] = Field(min_length=1)


class StatusChangeRequest(StrictRequestModel):
    pass


class OpportunityStageRegressionRequest(StrictRequestModel):
    expected_status: OpportunityStatus
    target_status: OpportunityStatus


class LoseOpportunityRequest(StatusChangeRequest):
    loss_reason: LossReason
    loss_reason_detail: LossReasonDetail | None = None

    @model_validator(mode="after")
    def validate_loss_reason_detail(self) -> Self:
        if self.loss_reason is LossReason.OTRO and self.loss_reason_detail is None:
            raise ValueError("loss_reason_detail is required when loss_reason is OTRO")
        if (
            self.loss_reason is not LossReason.OTRO
            and self.loss_reason_detail is not None
        ):
            raise ValueError(
                "loss_reason_detail is only allowed when loss_reason is OTRO"
            )
        return self


class ReopenOpportunityRequest(StrictRequestModel):
    command_id: UUID
    expected_status: Literal[OpportunityStatus.PERDIDA]


class AssigneeUpdate(StrictRequestModel):
    assigned_user_id: PositiveId | None
    expected_updated_at: datetime


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class QuotedProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductResponse
    quantity_kg: Decimal


class OpportunityStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_status: OpportunityStatus | None
    to_status: OpportunityStatus
    changed_at: datetime
    changed_by_user_id: int | None
    transition_kind: OpportunityTransitionKind


class OpportunityLossEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status_history_id: int
    reason: LossReason
    loss_reason_detail: str | None
    lost_at: datetime


class OpportunityWebIntake(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str | None


class OpportunitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OpportunityStatus
    source: LeadSource
    current_status_entered_at: datetime
    customer: CustomerSummary
    assigned_user: UserSummary | None
    products: list[QuotedProductResponse] = Field(
        validation_alias="opportunity_products"
    )
    created_at: datetime
    is_reopened: bool
    reopen_count: int


class OpportunityDetail(OpportunitySummary):
    history: list[OpportunityStatusHistoryResponse] = Field(
        validation_alias="status_history"
    )
    loss_reason: LossReason | None
    loss_reason_detail: str | None
    loss_events: list[OpportunityLossEventResponse]
    updated_at: datetime
    web_intake: OpportunityWebIntake | None = Field(validation_alias="lead_intake")


class ManualOpportunityCreateResponse(BaseModel):
    created: bool
    opportunity: OpportunityDetail
