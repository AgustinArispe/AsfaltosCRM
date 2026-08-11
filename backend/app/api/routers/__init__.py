from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.customer_imports import router as customer_imports_router
from app.api.routers.customers import router as customers_router
from app.api.routers.intake import router as intake_router
from app.api.routers.lost_opportunities import router as lost_opportunities_router
from app.api.routers.metrics import router as metrics_router
from app.api.routers.notifications import router as notifications_router
from app.api.routers.opportunities import router as opportunities_router
from app.api.routers.products import router as products_router
from app.api.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(intake_router)
api_router.include_router(notifications_router)
api_router.include_router(metrics_router)
api_router.include_router(customers_router)
api_router.include_router(customer_imports_router)
api_router.include_router(products_router)
api_router.include_router(opportunities_router)
api_router.include_router(lost_opportunities_router)
api_router.include_router(users_router)
