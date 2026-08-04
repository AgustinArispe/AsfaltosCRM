from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models import LeadSource, LossReason, OpportunityStatus
from app.schemas.common import StrictRequestModel
from app.schemas.customer import CustomerSummary
from app.schemas.product import ProductResponse


PositiveId = Annotated[int, Field(gt=0)]
PositiveQuantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=14, decimal_places=3),
]


class OpportunityCreate(StrictRequestModel):
    customer_id: PositiveId
    source: LeadSource
    assigned_user_id: PositiveId | None = None


class QuoteProductRequest(StrictRequestModel):
    product_id: PositiveId
    quantity_kg: PositiveQuantity


class QuoteRequest(StrictRequestModel):
    products: list[QuoteProductRequest] = Field(min_length=1)
    changed_by_user_id: PositiveId | None = None


class QuoteProductsUpdate(StrictRequestModel):
    products: list[QuoteProductRequest] = Field(min_length=1)


class StatusChangeRequest(StrictRequestModel):
    changed_by_user_id: PositiveId | None = None


class LoseOpportunityRequest(StatusChangeRequest):
    loss_reason: LossReason


class AssigneeUpdate(StrictRequestModel):
    assigned_user_id: PositiveId | None


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


class OpportunityDetail(OpportunitySummary):
    history: list[OpportunityStatusHistoryResponse] = Field(
        validation_alias="status_history"
    )
    loss_reason: LossReason | None
    updated_at: datetime
