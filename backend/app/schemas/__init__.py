from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import PaginatedResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetail,
    CustomerSummary,
    CustomerUpdate,
)
from app.schemas.lead_intake import WebLeadIntakeRequest, WebLeadIntakeResponse
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
    "CustomerDetail",
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
    "WebLeadIntakeRequest",
    "WebLeadIntakeResponse",
]
