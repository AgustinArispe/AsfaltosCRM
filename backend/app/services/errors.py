from app.models import OpportunityStatus


class DomainError(Exception):
    """Base class for business-rule failures independent of HTTP."""


class AuthenticationError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


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
