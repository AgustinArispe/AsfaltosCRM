from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import (
    CustomerImportAction,
    CustomerImportIssueCode,
    CustomerImportStatus,
    LossReason,
)
from app.schemas.common import StrictRequestModel
from app.schemas.opportunity import OpportunitySummary

NoteBody = Annotated[str, StringConstraints(min_length=1, max_length=20_000)]


class OpportunityNoteCreate(StrictRequestModel):
    client_generated_id: UUID
    body: NoteBody
    is_pinned: bool = False


class OpportunityNoteRevisionCreate(StrictRequestModel):
    command_id: UUID
    expected_revision: int = Field(gt=0)
    body: NoteBody | None = None
    is_pinned: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.body is None and self.is_pinned is None:
            raise ValueError("body or is_pinned is required")
        return self


class NoteRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_number: int
    body: str
    is_pinned: bool
    actor_user_id: int
    actor_name: str
    created_at: datetime


class OpportunityNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    opportunity_id: int
    author_user_id: int
    author_name: str
    created_at: datetime
    current_revision: NoteRevisionResponse


class NotePageResponse(BaseModel):
    items: list[OpportunityNoteResponse]
    next_cursor: str | None


class LossProductSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity_kg: Decimal


class LostOpportunityResponse(BaseModel):
    opportunity: OpportunitySummary
    loss_event_id: int
    loss_reason: LossReason
    lost_at: datetime
    quoted_total_kg: Decimal
    loss_products: list[LossProductSnapshotResponse]


class LostOpportunityPageResponse(BaseModel):
    items: list[LostOpportunityResponse]
    next_cursor: str | None


class StatisticBucket(BaseModel):
    key: str
    count: int
    quantity_kg: Decimal


class ProductStatisticBucket(BaseModel):
    product_id: int
    product_name: str
    count: int
    quantity_kg: Decimal


class LostStatisticsResponse(BaseModel):
    current_count: int
    current_quantity_kg: Decimal
    historical_loss_count: int
    historical_quantity_kg: Decimal
    reopened_count: int
    by_reason: list[StatisticBucket]
    by_product: list[ProductStatisticBucket]
    by_source: list[StatisticBucket]
    by_province: list[StatisticBucket]
    timeline: list[StatisticBucket]


class CustomerImportIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_name: str | None
    code: CustomerImportIssueCode
    message: str


class CustomerImportRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None
    action: CustomerImportAction
    resolved_customer_id: int | None
    issues: list[CustomerImportIssueResponse]


class CustomerImportReportResponse(BaseModel):
    id: int
    client_import_id: UUID
    file_sha256: str
    source_filename: str
    status: CustomerImportStatus
    version: int
    row_count: int
    create_count: int
    enrich_count: int
    unchanged_count: int
    error_count: int
    rows: list[CustomerImportRowResponse]
    created_at: datetime
    committed_at: datetime | None


class CustomerImportCommitRequest(StrictRequestModel):
    command_id: UUID
    expected_version: int = Field(gt=0)
    file_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class CustomerImportCommitResponse(BaseModel):
    batch_id: int
    status: CustomerImportStatus
    created_count: int
    enriched_count: int
    unchanged_count: int
    customer_ids: list[int]
    committed_at: datetime
