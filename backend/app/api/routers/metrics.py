from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.metrics import (
    MetricsOverviewResponse,
    MetricsPeriodResponse,
    MetricsQuery,
    OpportunityMetricsResponse,
    PipelineMetricsQuery,
    PipelineMetricsResponse,
    PipelineStatusMetricResponse,
    ProductMetricResponse,
    ProductMetricsResponse,
    ProvinceMetricResponse,
    ProvinceMetricsResponse,
    SourceMetricResponse,
    SourceMetricsResponse,
    TimelineDayOpportunitiesQuery,
    TimelineDayOpportunitiesResponse,
    TimelineMetricResponse,
    TimelineMetricsQuery,
    TimelineMetricsResponse,
    TimelineOpportunityItemResponse,
    TimelineOpportunityProductResponse,
    VolumeMetricsResponse,
)
from app.services.metrics_service import (
    BUSINESS_TIMEZONE_NAME,
    MetricsDimensions,
    MetricsFilters,
    MetricsPeriod,
    MetricsService,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _filters(query: MetricsQuery) -> MetricsFilters:
    return MetricsFilters(
        period=MetricsPeriod(
            start=query.from_.astimezone(UTC),
            end=query.to.astimezone(UTC),
        ),
        dimensions=_dimensions(query),
    )


def _dimensions(query: MetricsQuery | PipelineMetricsQuery) -> MetricsDimensions:
    return MetricsDimensions(
        source=query.source,
        product_id=query.product_id,
        province=query.province,
    )


def _period_response(period: MetricsPeriod) -> MetricsPeriodResponse:
    return MetricsPeriodResponse(start=period.start, to=period.end)


@router.get(
    "/overview",
    response_model=MetricsOverviewResponse,
    summary="Get commercial KPI overview",
    description=(
        "Created/open figures use opportunity creation time; won/lost figures and "
        "conversion rates use terminal-state entry time. The period is [from, to)."
    ),
)
def get_metrics_overview(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[MetricsQuery, Query()],
) -> MetricsOverviewResponse:
    filters = _filters(query)
    metrics = MetricsService(session).overview(filters)
    return MetricsOverviewResponse(
        period=_period_response(filters.period),
        opportunities=OpportunityMetricsResponse.model_validate(
            metrics.opportunities,
            from_attributes=True,
        ),
        volume_kg=VolumeMetricsResponse.model_validate(
            metrics.volume_kg,
            from_attributes=True,
        ),
    )


@router.get(
    "/products",
    response_model=ProductMetricsResponse,
    summary="Get metrics grouped by product",
)
def get_product_metrics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[MetricsQuery, Query()],
) -> ProductMetricsResponse:
    filters = _filters(query)
    return ProductMetricsResponse(
        period=_period_response(filters.period),
        items=[
            ProductMetricResponse.model_validate(item)
            for item in MetricsService(session).products(filters)
        ],
    )


@router.get(
    "/sources",
    response_model=SourceMetricsResponse,
    summary="Get metrics grouped by lead source",
)
def get_source_metrics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[MetricsQuery, Query()],
) -> SourceMetricsResponse:
    filters = _filters(query)
    return SourceMetricsResponse(
        period=_period_response(filters.period),
        items=[
            SourceMetricResponse.model_validate(item)
            for item in MetricsService(session).sources(filters)
        ],
    )


@router.get(
    "/provinces",
    response_model=ProvinceMetricsResponse,
    summary="Get metrics grouped by customer province",
    description="A null province represents customers without a recorded province.",
)
def get_province_metrics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[MetricsQuery, Query()],
) -> ProvinceMetricsResponse:
    filters = _filters(query)
    return ProvinceMetricsResponse(
        period=_period_response(filters.period),
        items=[
            ProvinceMetricResponse.model_validate(item)
            for item in MetricsService(session).provinces(filters)
        ],
    )


@router.get(
    "/timeline",
    response_model=TimelineMetricsResponse,
    summary="Get zero-filled day or month metric buckets",
    description=(
        "Calendar buckets use America/Argentina/Buenos_Aires. Created leads use "
        "creation time; won/lost figures use terminal-state entry time."
    ),
)
def get_timeline_metrics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[TimelineMetricsQuery, Query()],
) -> TimelineMetricsResponse:
    filters = _filters(query)
    return TimelineMetricsResponse(
        period=_period_response(filters.period),
        granularity=query.granularity,
        timezone=BUSINESS_TIMEZONE_NAME,
        items=[
            TimelineMetricResponse.model_validate(item)
            for item in MetricsService(session).timeline(
                filters,
                granularity=query.granularity,
            )
        ],
    )


@router.get(
    "/timeline/day-opportunities",
    response_model=TimelineDayOpportunitiesResponse,
    summary="Get Opportunities contributing to one timeline day",
    description=(
        "Returns a bounded page for one exact Buenos Aires calendar day and series. "
        "Created uses creation time; won/lost use current terminal-state entry time."
    ),
)
def get_timeline_day_opportunities(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[TimelineDayOpportunitiesQuery, Query()],
) -> TimelineDayOpportunitiesResponse:
    dimensions = _dimensions(query)
    opportunities, total = MetricsService(session).timeline_day_opportunities(
        bucket=query.bucket,
        series=query.series,
        dimensions=dimensions,
        page=query.page,
        page_size=query.page_size,
    )
    return TimelineDayOpportunitiesResponse(
        bucket=query.bucket,
        series=query.series,
        timezone=BUSINESS_TIMEZONE_NAME,
        page=query.page,
        page_size=query.page_size,
        total=total,
        items=[
            TimelineOpportunityItemResponse(
                opportunity_id=opportunity.id,
                customer_name=opportunity.customer.name,
                customer_company=opportunity.customer.company,
                current_status=opportunity.status,
                source=opportunity.source,
                products=[
                    TimelineOpportunityProductResponse(
                        product_id=line.product.id,
                        product_name=line.product.name,
                        quantity_kg=line.quantity_kg,
                        is_active=line.product.is_active,
                    )
                    for line in sorted(
                        opportunity.opportunity_products,
                        key=lambda item: (item.product.name, item.product.id),
                    )
                ],
            )
            for opportunity in opportunities
        ],
    )


@router.get(
    "/pipeline",
    response_model=PipelineMetricsResponse,
    summary="Get current opportunity status distribution",
    description="This is a current snapshot and does not accept a date period.",
)
def get_pipeline_metrics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    query: Annotated[PipelineMetricsQuery, Query()],
) -> PipelineMetricsResponse:
    return PipelineMetricsResponse(
        snapshot_at=datetime.now(UTC),
        items=[
            PipelineStatusMetricResponse.model_validate(item)
            for item in MetricsService(session).pipeline(_dimensions(query))
        ],
    )
