from datetime import datetime

from app.models import OpportunityStatus


class DomainError(Exception):
    """Base class for business-rule failures independent of HTTP."""


class AuthenticationError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class IntakeAuthenticationError(DomainError):
    """Raised when an external intake request cannot be authenticated."""


class CustomerIdentityConflictError(DomainError):
    """Raised when intake identity signals resolve ambiguously."""


class LeadIntakeIdempotencyConflictError(DomainError):
    """Raised when an external ID is replayed with a different payload."""


class InvalidLeadIntakeError(DomainError):
    """Raised when an intake DTO violates its application contract."""


class InvalidWhatsAppMessageError(DomainError):
    """Raised when a WhatsApp message violates its domain contract."""


class WhatsAppFreeformWindowClosedError(InvalidWhatsAppMessageError):
    """Raised when freeform sending requires an approved template."""


class InvalidWhatsAppCursorError(DomainError):
    """Raised when an opaque WhatsApp API cursor cannot be validated."""


class WhatsAppIdempotencyConflictError(DomainError):
    """Raised when a WhatsApp idempotency key is reused with another payload."""


class WhatsAppConversationResolutionError(DomainError):
    """Raised when an unresolved conversation cannot perform an operation."""


class WhatsAppOpportunityAssociationError(DomainError):
    """Raised when a conversation and opportunity cannot be associated."""


class WhatsAppReplyInProgressError(DomainError):
    """Raised when another direct reply has an uncertain or active dispatch."""


class WhatsAppBroadcastConflictError(DomainError):
    """Raised when a Broadcast lifecycle or idempotency command conflicts."""


class InvalidWhatsAppBroadcastError(DomainError):
    """Raised when Broadcast inputs cannot be safely confirmed or dispatched."""


class MetricsTimelinePeriodTooLargeError(DomainError):
    code = "METRICS_TIMELINE_PERIOD_TOO_LARGE"

    def __init__(
        self,
        *,
        granularity: str,
        requested_bucket_count: int,
        maximum_bucket_count: int,
    ) -> None:
        self.granularity = granularity
        self.requested_bucket_count = requested_bucket_count
        self.maximum_bucket_count = maximum_bucket_count
        super().__init__(
            f"Timeline {granularity} period requests {requested_bucket_count} "
            f"buckets; maximum is {maximum_bucket_count}"
        )


class EntityNotFoundError(DomainError):
    def __init__(self, entity_name: str, entity_id: int) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        super().__init__(f"{entity_name} with id {entity_id} was not found")


class DuplicateEntityError(DomainError):
    def __init__(self, entity_name: str, field_name: str) -> None:
        self.entity_name = entity_name
        self.field_name = field_name
        super().__init__(f"{entity_name} with that {field_name} already exists")


class DeletedCustomerError(DomainError):
    def __init__(self, customer_id: int) -> None:
        self.customer_id = customer_id
        super().__init__(f"Customer with id {customer_id} is deleted")


class InactiveUserError(DomainError):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(f"User with id {user_id} is inactive")


class InactiveProductError(DomainError):
    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product with id {product_id} is inactive")


class InvalidStateTransitionError(DomainError):
    def __init__(
        self,
        opportunity_id: int,
        from_status: OpportunityStatus,
        to_status: OpportunityStatus,
    ) -> None:
        self.opportunity_id = opportunity_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Opportunity {opportunity_id} cannot transition from "
            f"{from_status.value} to {to_status.value}"
        )


class InvalidQuoteProductsError(DomainError):
    """Raised when the current quote product set violates a business rule."""


class InvalidLossReasonError(DomainError):
    """Raised when marking an opportunity lost without a valid reason."""


class RevisionConflictError(DomainError):
    """Raised for a stale append-only note command."""


class StaleWriteConflictError(DomainError):
    """Raised when a conditional Customer or Opportunity mutation is stale."""

    def __init__(self, *, resource: str, current_updated_at: datetime) -> None:
        self.resource = resource
        self.current_updated_at = current_updated_at
        super().__init__(f"{resource} was updated by another change")


class IdempotencyConflictError(DomainError):
    """Raised when a CRM command UUID is reused with different input."""


class InvalidCustomerImportError(DomainError):
    """Raised when a Customer import cannot be validated or committed."""


class ClosedOpportunityError(DomainError):
    def __init__(
        self,
        opportunity_id: int,
        status: OpportunityStatus,
    ) -> None:
        self.opportunity_id = opportunity_id
        self.status = status
        super().__init__(
            f"Opportunity {opportunity_id} is closed with status {status.value}"
        )
