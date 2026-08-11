from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import LeadSource, LossReason
from app.schemas import (
    LossProductSnapshotResponse,
    LostOpportunityPageResponse,
    LostOpportunityResponse,
    LostStatisticsResponse,
    OpportunitySummary,
)
from app.services.lost_opportunity_service import LostFilters, LostOpportunityService

router = APIRouter(prefix="/lost-opportunities", tags=["lost opportunities"])


def _filters(
    search: str | None,
    reason: list[LossReason] | None,
    customer_id: int | None,
    province: str | None,
    product_id: int | None,
    source: LeadSource | None,
    lost_from: datetime | None,
    lost_to: datetime | None,
) -> LostFilters:
    return LostFilters(
        search=search,
        reasons=tuple(reason or []),
        customer_id=customer_id,
        province=province,
        product_id=product_id,
        source=source,
        lost_from=lost_from,
        lost_to=lost_to,
    )


@router.get("", response_model=LostOpportunityPageResponse)
def list_lost_opportunities(
    session: DatabaseSession,
    _current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=200)] = None,
    reason: Annotated[list[LossReason] | None, Query()] = None,
    customer_id: Annotated[int | None, Query(gt=0)] = None,
    province: Annotated[str | None, Query(max_length=200)] = None,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    source: LeadSource | None = None,
    lost_from: datetime | None = None,
    lost_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
) -> LostOpportunityPageResponse:
    page = LostOpportunityService(session).list_current(
        _filters(
            search,
            reason,
            customer_id,
            province,
            product_id,
            source,
            lost_from,
            lost_to,
        ),
        limit=limit,
        cursor=cursor,
    )
    return LostOpportunityPageResponse(
        items=[
            LostOpportunityResponse(
                opportunity=OpportunitySummary.model_validate(item.opportunity),
                loss_event_id=item.loss_event_id,
                loss_reason=item.loss_reason,
                lost_at=item.lost_at,
                quoted_total_kg=item.quoted_total_kg,
                loss_products=[
                    LossProductSnapshotResponse.model_validate(product)
                    for product in item.loss_products
                ],
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get("/statistics", response_model=LostStatisticsResponse)
def lost_statistics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=200)] = None,
    reason: Annotated[list[LossReason] | None, Query()] = None,
    customer_id: Annotated[int | None, Query(gt=0)] = None,
    province: Annotated[str | None, Query(max_length=200)] = None,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    source: LeadSource | None = None,
    lost_from: datetime | None = None,
    lost_to: datetime | None = None,
) -> LostStatisticsResponse:
    result = LostOpportunityService(session).statistics(
        _filters(
            search,
            reason,
            customer_id,
            province,
            product_id,
            source,
            lost_from,
            lost_to,
        )
    )
    return LostStatisticsResponse.model_validate(result, from_attributes=True)
