from fastapi import APIRouter, status

from app.api.dependencies import DatabaseSession
from app.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse], summary="List products")
def list_products(
    session: DatabaseSession,
    include_inactive: bool = False,
) -> list[ProductResponse]:
    products = ProductService(session).list_products(
        include_inactive=include_inactive
    )
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
) -> ProductResponse:
    product = ProductService(session).update_product(
        product_id,
        payload.model_dump(exclude_unset=True),
    )
    return ProductResponse.model_validate(product)
