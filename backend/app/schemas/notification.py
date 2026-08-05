from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import NotificationType, OpportunityStatus
from app.schemas.common import StrictRequestModel


class NotificationActionRequest(StrictRequestModel):
    pass


class NotificationCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: str | None


class NotificationOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OpportunityStatus
    current_status_entered_at: datetime
    customer: NotificationCustomerResponse


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    created_at: datetime
    read_at: datetime | None
    resolved_at: datetime | None
    opportunity: NotificationOpportunityResponse


class NotificationReadAllResponse(BaseModel):
    updated_count: int
