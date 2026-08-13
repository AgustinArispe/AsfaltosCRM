from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    Pagination,
    SupervisorUser,
)
from app.models import UserRole
from app.schemas import (
    CustomerCreate,
    CustomerDetail,
    CustomerSummary,
    CustomerUpdate,
    PaginatedResponse,
)
from app.services.customer_service import CustomerService
from app.services.errors import PermissionDeniedError

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post(
    "",
    response_model=CustomerSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer",
)
def create_customer(
    payload: CustomerCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CustomerSummary:
    if (
        current_user.role is UserRole.VENDEDOR
        and "legendary_historical_override" in payload.model_fields_set
    ):
        raise PermissionDeniedError(
            "Only supervisors can set the legendary historical override"
        )
    customer = CustomerService(session).create_customer(
        **payload.model_dump(), actor_user_id=current_user.id
    )
    return CustomerSummary.model_validate(customer)


@router.get(
    "",
    response_model=PaginatedResponse[CustomerSummary],
    summary="List customers",
)
def list_customers(
    session: DatabaseSession,
    pagination: Pagination,
    _current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=200)] = None,
    include_deleted: bool = False,
) -> PaginatedResponse[CustomerSummary]:
    customers, total = CustomerService(session).list_customers(
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        include_deleted=include_deleted,
    )
    return PaginatedResponse(
        items=[CustomerSummary.model_validate(customer) for customer in customers],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerDetail,
    summary="Get customer",
)
def get_customer(
    customer_id: int,
    session: DatabaseSession,
    _current_user: CurrentUser,
) -> CustomerDetail:
    customer = CustomerService(session).get_customer(customer_id)
    return CustomerDetail.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerSummary,
    summary="Update customer",
)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> CustomerSummary:
    if (
        current_user.role is UserRole.VENDEDOR
        and "legendary_historical_override" in payload.model_fields_set
    ):
        raise PermissionDeniedError(
            "Only supervisors can change the legendary historical override"
        )
    customer = CustomerService(session).update_customer(
        customer_id,
        payload.model_dump(exclude={"expected_updated_at"}, exclude_unset=True),
        expected_updated_at=payload.expected_updated_at,
        actor_user_id=current_user.id,
    )
    return CustomerSummary.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete customer",
    description="Idempotent: an already deleted customer also returns 204.",
)
def delete_customer(
    customer_id: int,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> Response:
    CustomerService(session).soft_delete_customer(customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
