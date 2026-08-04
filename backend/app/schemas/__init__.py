from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerSummary, CustomerUpdate
from app.schemas.opportunity import (
    AssigneeUpdate,
    LoseOpportunityRequest,
    OpportunityCreate,
    OpportunityDetail,
    OpportunitySummary,
    QuoteProductRequest,
    QuoteProductsUpdate,
    QuoteRequest,
    StatusChangeRequest,
)
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.schemas.user import PasswordUpdate, UserCreate, UserResponse, UserUpdate

__all__ = [
    "AssigneeUpdate",
    "CustomerCreate",
    "CustomerSummary",
    "CustomerUpdate",
    "LoginRequest",
    "LoseOpportunityRequest",
    "OpportunityCreate",
    "OpportunityDetail",
    "OpportunitySummary",
    "PaginatedResponse",
    "PasswordUpdate",
    "ProductCreate",
    "ProductResponse",
    "ProductUpdate",
    "QuoteProductRequest",
    "QuoteProductsUpdate",
    "QuoteRequest",
    "StatusChangeRequest",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
