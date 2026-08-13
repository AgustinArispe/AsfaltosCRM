from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    Pagination,
    SupervisorUser,
)
from app.models import LeadSource, OpportunityStatus, UserRole
from app.schemas import (
    AssigneeUpdate,
    LoseOpportunityRequest,
    NotePageResponse,
    NoteRevisionResponse,
    OpportunityCreate,
    OpportunityDetail,
    OpportunityNoteCreate,
    OpportunityNoteResponse,
    OpportunityNoteRevisionCreate,
    OpportunitySummary,
    PaginatedResponse,
    QuoteProductsUpdate,
    QuoteRequest,
    ReopenOpportunityRequest,
    StatusChangeRequest,
)
from app.services import OpportunityService, QuoteProductInput
from app.services.errors import PermissionDeniedError
from app.services.opportunity_note_service import OpportunityNoteService
from app.services.opportunity_query_service import OpportunityQueryService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _quote_inputs(
    payload: QuoteRequest | QuoteProductsUpdate,
) -> list[QuoteProductInput]:
    return [
        QuoteProductInput(
            product_id=product.product_id,
            quantity_kg=product.quantity_kg,
        )
        for product in payload.products
    ]


def _detail(session: DatabaseSession, opportunity_id: int) -> OpportunityDetail:
    opportunity = OpportunityQueryService(session).get_detail(opportunity_id)
    return OpportunityDetail.model_validate(opportunity)


@router.post(
    "",
    response_model=OpportunityDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create opportunity in NUEVA",
)
def create_opportunity(
    payload: OpportunityCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> OpportunityDetail:
    if current_user.role is UserRole.VENDEDOR and payload.assigned_user_id is not None:
        raise PermissionDeniedError("Only supervisors can assign opportunity owners")
    opportunity = OpportunityService(session).create_opportunity(
        customer_id=payload.customer_id,
        source=payload.source,
        assigned_user_id=payload.assigned_user_id,
        changed_by_user_id=current_user.id,
    )
    return _detail(session, opportunity.id)


@router.get(
    "",
    response_model=PaginatedResponse[OpportunitySummary],
    summary="List opportunities for pipeline views",
)
def list_opportunities(
    session: DatabaseSession,
    pagination: Pagination,
    _current_user: CurrentUser,
    status_filter: Annotated[OpportunityStatus | None, Query(alias="status")] = None,
    customer_id: Annotated[int | None, Query(gt=0)] = None,
    assigned_user_id: Annotated[int | None, Query(gt=0)] = None,
    source: LeadSource | None = None,
) -> PaginatedResponse[OpportunitySummary]:
    opportunities, total = OpportunityQueryService(session).list_opportunities(
        page=pagination.page,
        page_size=pagination.page_size,
        status=status_filter,
        customer_id=customer_id,
        assigned_user_id=assigned_user_id,
        source=source,
    )
    return PaginatedResponse(
        items=[
            OpportunitySummary.model_validate(opportunity)
            for opportunity in opportunities
        ],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/{opportunity_id}",
    response_model=OpportunityDetail,
    summary="Get opportunity detail and status history",
)
def get_opportunity(
    opportunity_id: int,
    session: DatabaseSession,
    _current_user: CurrentUser,
) -> OpportunityDetail:
    return _detail(session, opportunity_id)


@router.post(
    "/{opportunity_id}/quote",
    response_model=OpportunityDetail,
    summary="Quote a new opportunity",
)
def quote_opportunity(
    opportunity_id: int,
    payload: QuoteRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> OpportunityDetail:
    OpportunityService(session).quote_opportunity(
        opportunity_id,
        _quote_inputs(payload),
        changed_by_user_id=current_user.id,
    )
    return _detail(session, opportunity_id)


@router.post(
    "/{opportunity_id}/move-to-negotiation",
    response_model=OpportunityDetail,
    summary="Move quoted opportunity to negotiation",
)
def move_to_negotiation(
    opportunity_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
    _payload: Annotated[StatusChangeRequest | None, Body()] = None,
) -> OpportunityDetail:
    OpportunityService(session).move_to_negotiation(
        opportunity_id,
        changed_by_user_id=current_user.id,
    )
    return _detail(session, opportunity_id)


@router.post(
    "/{opportunity_id}/win",
    response_model=OpportunityDetail,
    summary="Mark negotiating opportunity as won",
)
def mark_as_won(
    opportunity_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
    _payload: Annotated[StatusChangeRequest | None, Body()] = None,
) -> OpportunityDetail:
    OpportunityService(session).mark_as_won(
        opportunity_id,
        changed_by_user_id=current_user.id,
    )
    return _detail(session, opportunity_id)


@router.post(
    "/{opportunity_id}/lose",
    response_model=OpportunityDetail,
    summary="Mark an open opportunity as lost",
)
def mark_as_lost(
    opportunity_id: int,
    payload: LoseOpportunityRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> OpportunityDetail:
    OpportunityService(session).mark_as_lost(
        opportunity_id,
        payload.loss_reason,
        changed_by_user_id=current_user.id,
    )
    return _detail(session, opportunity_id)


@router.put(
    "/{opportunity_id}/quote-products",
    response_model=OpportunityDetail,
    summary="Replace current quoted products",
)
def update_quote_products(
    opportunity_id: int,
    payload: QuoteProductsUpdate,
    session: DatabaseSession,
    _current_user: CurrentUser,
) -> OpportunityDetail:
    OpportunityService(session).update_quote_products(
        opportunity_id,
        _quote_inputs(payload),
        expected_updated_at=payload.expected_updated_at,
    )
    return _detail(session, opportunity_id)


@router.put(
    "/{opportunity_id}/assignee",
    response_model=OpportunityDetail,
    summary="Assign or unassign opportunity owner",
)
def update_assignee(
    opportunity_id: int,
    payload: AssigneeUpdate,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> OpportunityDetail:
    OpportunityService(session).assign_user(
        opportunity_id,
        payload.assigned_user_id,
        expected_updated_at=payload.expected_updated_at,
    )
    return _detail(session, opportunity_id)


@router.post(
    "/{opportunity_id}/reopen",
    response_model=OpportunityDetail,
    summary="Reopen a lost opportunity into negotiation",
)
def reopen_opportunity(
    opportunity_id: int,
    payload: ReopenOpportunityRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> OpportunityDetail:
    OpportunityService(session).reopen(
        opportunity_id,
        command_id=payload.command_id,
        expected_status=payload.expected_status,
        changed_by_user_id=current_user.id,
    )
    return _detail(session, opportunity_id)


@router.post(
    "/{opportunity_id}/notes",
    response_model=OpportunityNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    opportunity_id: int,
    payload: OpportunityNoteCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> OpportunityNoteResponse:
    note = OpportunityNoteService(session).create(
        opportunity_id,
        command_id=payload.client_generated_id,
        body=payload.body,
        is_pinned=payload.is_pinned,
        actor_user_id=current_user.id,
    )
    return OpportunityNoteResponse.model_validate(note)


@router.get(
    "/{opportunity_id}/notes",
    response_model=NotePageResponse,
)
def list_notes(
    opportunity_id: int,
    session: DatabaseSession,
    _current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=200)] = None,
    pinned: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
) -> NotePageResponse:
    page = OpportunityNoteService(session).list_current(
        opportunity_id,
        search=search,
        pinned=pinned,
        limit=limit,
        cursor=cursor,
    )
    return NotePageResponse(
        items=[OpportunityNoteResponse.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
    )


@router.post(
    "/{opportunity_id}/notes/{note_id}/revisions",
    response_model=OpportunityNoteResponse,
)
def revise_note(
    opportunity_id: int,
    note_id: int,
    payload: OpportunityNoteRevisionCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> OpportunityNoteResponse:
    note = OpportunityNoteService(session).revise(
        opportunity_id,
        note_id,
        command_id=payload.command_id,
        expected_revision=payload.expected_revision,
        body=payload.body,
        is_pinned=payload.is_pinned,
        actor_user_id=current_user.id,
    )
    return OpportunityNoteResponse.model_validate(note)


@router.get(
    "/{opportunity_id}/notes/{note_id}/revisions",
    response_model=list[NoteRevisionResponse],
)
def list_note_revisions(
    opportunity_id: int,
    note_id: int,
    session: DatabaseSession,
    _current_user: CurrentUser,
) -> list[NoteRevisionResponse]:
    revisions = OpportunityNoteService(session).list_revisions(opportunity_id, note_id)
    return [NoteRevisionResponse.model_validate(revision) for revision in revisions]
