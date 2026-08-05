from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, DatabaseSession, SupervisorUser
from app.models import UserRole
from app.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.services.errors import PermissionDeniedError
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse], summary="List products")
def list_products(
    session: DatabaseSession,
    current_user: CurrentUser,
    include_inactive: bool = False,
) -> list[ProductResponse]:
    if include_inactive and current_user.role is UserRole.VENDEDOR:
        raise PermissionDeniedError("Only supervisors can list inactive products")
    products = ProductService(session).list_products(include_inactive=include_inactive)
    return [ProductResponse.model_validate(product) for product in products]


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
)
def create_product(
    payload: ProductCreate,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> ProductResponse:
    product = ProductService(session).create_product(name=payload.name)
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update or deactivate product",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> ProductResponse:
    product = ProductService(session).update_product(
        product_id,
        payload.model_dump(exclude_unset=True),
    )
    return ProductResponse.model_validate(product)
