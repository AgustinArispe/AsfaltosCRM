from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.customers import router as customers_router
from app.api.routers.opportunities import router as opportunities_router
from app.api.routers.products import router as products_router
from app.api.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(customers_router)
api_router.include_router(products_router)
api_router.include_router(opportunities_router)
api_router.include_router(users_router)
