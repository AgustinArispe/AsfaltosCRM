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

__all__ = [
    "AssigneeUpdate",
    "CustomerCreate",
    "CustomerSummary",
    "CustomerUpdate",
    "LoseOpportunityRequest",
    "OpportunityCreate",
    "OpportunityDetail",
    "OpportunitySummary",
    "PaginatedResponse",
    "ProductCreate",
    "ProductResponse",
    "ProductUpdate",
    "QuoteProductRequest",
    "QuoteProductsUpdate",
    "QuoteRequest",
    "StatusChangeRequest",
]
