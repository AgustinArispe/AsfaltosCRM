from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models import LeadSource, OpportunityStatus
from app.schemas.common import StrictRequestModel
from app.services.metrics_service import (
    TimelineGranularity,
    TimelineOpportunitySeries,
)

ProvinceFilter = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class MetricsQuery(StrictRequestModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: datetime = Field(alias="from")
    to: datetime
    source: LeadSource | None = None
    product_id: int | None = Field(default=None, gt=0)
    province: ProvinceFilter | None = None

    @model_validator(mode="after")
    def validate_period(self) -> Self:
        if (
            self.from_.tzinfo is None
            or self.from_.utcoffset() is None
            or self.to.tzinfo is None
            or self.to.utcoffset() is None
        ):
            raise ValueError("from and to must include a timezone offset")
        if self.from_ >= self.to:
            raise ValueError("from must be earlier than to")
        return self


class TimelineMetricsQuery(MetricsQuery):
    granularity: TimelineGranularity = TimelineGranularity.DAY


class PipelineMetricsQuery(StrictRequestModel):
    source: LeadSource | None = None
    product_id: int | None = Field(default=None, gt=0)
    province: ProvinceFilter | None = None


class TimelineDayOpportunitiesQuery(PipelineMetricsQuery):
    bucket: date
    series: TimelineOpportunitySeries
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MetricsPeriodResponse(BaseModel):
    start: datetime = Field(
        validation_alias=AliasChoices("start", "from"),
        serialization_alias="from",
    )
    to: datetime


class OpportunityMetricsResponse(BaseModel):
    created: int
    won: int
    lost: int
    open: int
    conversion_rate: Decimal | None


class VolumeMetricsResponse(BaseModel):
    quoted: Decimal
    won: Decimal
    lost: Decimal
    open: Decimal
    conversion_rate: Decimal | None


class MetricsOverviewResponse(BaseModel):
    period: MetricsPeriodResponse
    opportunities: OpportunityMetricsResponse
    volume_kg: VolumeMetricsResponse


class ProductMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    opportunities_quoted: int
    kg_quoted: Decimal
    opportunities_won: int
    kg_won: Decimal
    opportunities_lost: int
    kg_lost: Decimal
    conversion_rate_opportunities: Decimal | None
    conversion_rate_kg: Decimal | None


class ProductMetricsResponse(BaseModel):
    period: MetricsPeriodResponse
    items: list[ProductMetricResponse]


class SourceMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: LeadSource
    created: int
    won: int
    lost: int
    conversion_rate: Decimal | None


class SourceMetricsResponse(BaseModel):
    period: MetricsPeriodResponse
    items: list[SourceMetricResponse]


class ProvinceMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    province: str | None
    opportunities_created: int
    opportunities_won: int
    opportunities_lost: int
    conversion_rate: Decimal | None
    kg_quoted: Decimal
    kg_won: Decimal
    kg_lost: Decimal


class ProvinceMetricsResponse(BaseModel):
    period: MetricsPeriodResponse
    items: list[ProvinceMetricResponse]


class TimelineMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bucket: date
    leads_created: int
    won: int
    lost: int
    kg_won: Decimal
    kg_lost: Decimal


class TimelineMetricsResponse(BaseModel):
    period: MetricsPeriodResponse
    granularity: TimelineGranularity
    timezone: str
    items: list[TimelineMetricResponse]


class TimelineOpportunityProductResponse(BaseModel):
    product_id: int
    product_name: str
    quantity_kg: Decimal
    is_active: bool


class TimelineOpportunityItemResponse(BaseModel):
    opportunity_id: int
    customer_name: str
    customer_company: str | None
    current_status: OpportunityStatus
    source: LeadSource
    products: list[TimelineOpportunityProductResponse]


class TimelineDayOpportunitiesResponse(BaseModel):
    bucket: date
    series: TimelineOpportunitySeries
    timezone: str
    page: int
    page_size: int
    total: int
    items: list[TimelineOpportunityItemResponse]


class PipelineStatusMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: OpportunityStatus
    count: int


class PipelineMetricsResponse(BaseModel):
    snapshot_at: datetime
    items: list[PipelineStatusMetricResponse]
