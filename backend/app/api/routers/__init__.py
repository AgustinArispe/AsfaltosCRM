from fastapi import APIRouter

from app.api.routers.customers import router as customers_router
from app.api.routers.opportunities import router as opportunities_router
from app.api.routers.products import router as products_router


api_router = APIRouter()
api_router.include_router(customers_router)
api_router.include_router(products_router)
api_router.include_router(opportunities_router)
