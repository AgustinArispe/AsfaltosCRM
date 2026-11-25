from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import LeadSource, LossReason
from app.schemas import (
    LossProductSnapshotResponse,
    LostOpportunityPageResponse,
    LostOpportunityResponse,
    LostStatisticsResponse,
    OpportunitySummary,
)
from app.schemas.crm_commercial import WonFilterOptionsResponse
from app.services.lost_opportunity_service import LostFilters, LostOpportunityService

router = APIRouter(prefix="/lost-opportunities", tags=["lost opportunities"])


def _filters(
    search: Annotated[str | None, Query(max_length=200)] = None,
    reason: Annotated[list[LossReason] | None, Query()] = None,
    customer_id: Annotated[int | None, Query(gt=0)] = None,
    province: Annotated[str | None, Query(max_length=200)] = None,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    source: LeadSource | None = None,
    assigned_user_id: Annotated[int | None, Query(gt=0)] = None,
    unassigned: bool = False,
    lost_from: datetime | None = None,
    lost_to: datetime | None = None,
) -> LostFilters:
    if assigned_user_id is not None and unassigned:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "assigned_user_id and unassigned are mutually exclusive",
        )
    if (lost_from is not None and lost_from.tzinfo is None) or (
        lost_to is not None and lost_to.tzinfo is None
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "lost dates must include a timezone"
        )
    if lost_from is not None and lost_to is not None and lost_from >= lost_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "lost_from must be before lost_to"
        )
    return LostFilters(
        search=search,
        reasons=tuple(reason or []),
        customer_id=customer_id,
        province=province,
        product_id=product_id,
        source=source,
        lost_from=lost_from,
        lost_to=lost_to,
        assigned_user_id=assigned_user_id,
        unassigned=unassigned,
    )


@router.get("", response_model=LostOpportunityPageResponse)
def list_lost_opportunities(
    session: DatabaseSession,
    _current_user: CurrentUser,
    filters: Annotated[LostFilters, Depends(_filters)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
) -> LostOpportunityPageResponse:
    page = LostOpportunityService(session).list_current(
        filters, limit=limit, cursor=cursor
    )
    return LostOpportunityPageResponse(
        items=[
            LostOpportunityResponse(
                opportunity=OpportunitySummary.model_validate(item.opportunity),
                loss_event_id=item.loss_event_id,
                loss_reason=item.loss_reason,
                loss_reason_detail=item.loss_reason_detail,
                from_status=item.from_status,
                customer_province=item.customer_province,
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
    filters: Annotated[LostFilters, Depends(_filters)],
) -> LostStatisticsResponse:
    return LostStatisticsResponse.model_validate(
        LostOpportunityService(session).statistics(filters), from_attributes=True
    )


@router.get("/filter-options", response_model=WonFilterOptionsResponse)
def lost_filter_options(
    session: DatabaseSession, _current_user: CurrentUser
) -> WonFilterOptionsResponse:
    return WonFilterOptionsResponse.model_validate(
        LostOpportunityService(session).filter_options(), from_attributes=True
    )
