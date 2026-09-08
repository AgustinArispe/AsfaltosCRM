from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models import LeadSource
from app.schemas.crm_commercial import (
    WonFilterOptionsResponse,
    WonOpportunityPageResponse,
    WonOpportunityResponse,
    WonStatisticsResponse,
)
from app.schemas.opportunity import OpportunitySummary
from app.services.won_opportunity_service import WonFilters, WonOpportunityQueryService

router = APIRouter(prefix="/won-opportunities", tags=["won opportunities"])


def _filters(
    search: str | None,
    product_id: int | None,
    source: LeadSource | None,
    province: str | None,
    assigned_user_id: int | None,
    unassigned: bool,
    won_from: datetime | None,
    won_to: datetime | None,
) -> WonFilters:
    if assigned_user_id is not None and unassigned:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "assigned_user_id and unassigned are mutually exclusive",
        )
    if (won_from is not None and won_from.tzinfo is None) or (
        won_to is not None and won_to.tzinfo is None
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "won dates must include a timezone"
        )
    if won_from is not None and won_to is not None and won_from >= won_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "won_from must be before won_to"
        )
    return WonFilters(
        search,
        product_id,
        source,
        province,
        assigned_user_id,
        unassigned,
        won_from,
        won_to,
    )


@router.get("", response_model=WonOpportunityPageResponse)
def list_won_opportunities(
    session: DatabaseSession,
    _current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=200)] = None,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    source: LeadSource | None = None,
    province: Annotated[str | None, Query(max_length=200)] = None,
    assigned_user_id: Annotated[int | None, Query(gt=0)] = None,
    unassigned: bool = False,
    won_from: datetime | None = None,
    won_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
) -> WonOpportunityPageResponse:
    page = WonOpportunityQueryService(session).list(
        _filters(
            search,
            product_id,
            source,
            province,
            assigned_user_id,
            unassigned,
            won_from,
            won_to,
        ),
        limit=limit,
        cursor=cursor,
    )
    return WonOpportunityPageResponse(
        items=[
            WonOpportunityResponse(
                opportunity=OpportunitySummary.model_validate(item.opportunity),
                won_at=item.won_at,
                won_total_kg=item.won_total_kg,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get("/statistics", response_model=WonStatisticsResponse)
def won_statistics(
    session: DatabaseSession,
    _current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=200)] = None,
    product_id: Annotated[int | None, Query(gt=0)] = None,
    source: LeadSource | None = None,
    province: Annotated[str | None, Query(max_length=200)] = None,
    assigned_user_id: Annotated[int | None, Query(gt=0)] = None,
    unassigned: bool = False,
    won_from: datetime | None = None,
    won_to: datetime | None = None,
) -> WonStatisticsResponse:
    result = WonOpportunityQueryService(session).statistics(
        _filters(
            search,
            product_id,
            source,
            province,
            assigned_user_id,
            unassigned,
            won_from,
            won_to,
        )
    )
    return WonStatisticsResponse(
        won_count=result.won_count, won_quantity_kg=result.won_quantity_kg
    )


@router.get("/filter-options", response_model=WonFilterOptionsResponse)
def won_filter_options(
    session: DatabaseSession, _current_user: CurrentUser
) -> WonFilterOptionsResponse:
    return WonFilterOptionsResponse.model_validate(
        WonOpportunityQueryService(session).filter_options(), from_attributes=True
    )
