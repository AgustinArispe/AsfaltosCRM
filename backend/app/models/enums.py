from enum import Enum, StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum


class UserRole(StrEnum):
    SUPERVISOR = "SUPERVISOR"
    VENDEDOR = "VENDEDOR"


class LeadSource(StrEnum):
    WEB = "WEB"
    WHATSAPP = "WHATSAPP"


class OpportunityStatus(StrEnum):
    NUEVA = "NUEVA"
    COTIZADA = "COTIZADA"
    NEGOCIACION = "NEGOCIACION"
    GANADA = "GANADA"
    PERDIDA = "PERDIDA"


class LossReason(StrEnum):
    PRECIO = "PRECIO"
    SIN_RESPUESTA = "SIN_RESPUESTA"
    COMPETENCIA = "COMPETENCIA"
    PROYECTO_CANCELADO = "PROYECTO_CANCELADO"
    OTRO = "OTRO"


class NotificationType(StrEnum):
    OPPORTUNITY_STALE = "OPPORTUNITY_STALE"


class WhatsAppConversationResolution(StrEnum):
    RESOLVED = "RESOLVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class WhatsAppDirection(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class WhatsAppMessageType(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"


class WhatsAppProviderState(StrEnum):
    RECEIVED = "RECEIVED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class WhatsAppDispatchState(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    ACCEPTED = "ACCEPTED"
    DEFINITIVE_FAILED = "DEFINITIVE_FAILED"
    UNKNOWN = "UNKNOWN"


class WhatsAppOpportunityLinkSource(StrEnum):
    AUTO_NEW_CONTACT = "AUTO_NEW_CONTACT"
    MANUAL = "MANUAL"


class WhatsAppStorageStatus(StrEnum):
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"


def _values(enum_class: type[Enum]) -> list[str]:
    return [member.value for member in enum_class]


USER_ROLE_DB_ENUM = SQLAlchemyEnum(
    UserRole,
    name="user_role_enum",
    values_callable=_values,
    validate_strings=True,
)
LEAD_SOURCE_DB_ENUM = SQLAlchemyEnum(
    LeadSource,
    name="lead_source_enum",
    values_callable=_values,
    validate_strings=True,
)
OPPORTUNITY_STATUS_DB_ENUM = SQLAlchemyEnum(
    OpportunityStatus,
    name="opportunity_status_enum",
    values_callable=_values,
    validate_strings=True,
)
LOSS_REASON_DB_ENUM = SQLAlchemyEnum(
    LossReason,
    name="loss_reason_enum",
    values_callable=_values,
    validate_strings=True,
)
NOTIFICATION_TYPE_DB_ENUM = SQLAlchemyEnum(
    NotificationType,
    name="notification_type_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_CONVERSATION_RESOLUTION_DB_ENUM = SQLAlchemyEnum(
    WhatsAppConversationResolution,
    name="whatsapp_conversation_resolution_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_DIRECTION_DB_ENUM = SQLAlchemyEnum(
    WhatsAppDirection,
    name="whatsapp_direction_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_MESSAGE_TYPE_DB_ENUM = SQLAlchemyEnum(
    WhatsAppMessageType,
    name="whatsapp_message_type_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_PROVIDER_STATE_DB_ENUM = SQLAlchemyEnum(
    WhatsAppProviderState,
    name="whatsapp_provider_state_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_DISPATCH_STATE_DB_ENUM = SQLAlchemyEnum(
    WhatsAppDispatchState,
    name="whatsapp_dispatch_state_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_OPPORTUNITY_LINK_SOURCE_DB_ENUM = SQLAlchemyEnum(
    WhatsAppOpportunityLinkSource,
    name="whatsapp_opportunity_link_source_enum",
    values_callable=_values,
    validate_strings=True,
)
WHATSAPP_STORAGE_STATUS_DB_ENUM = SQLAlchemyEnum(
    WhatsAppStorageStatus,
    name="whatsapp_storage_status_enum",
    values_callable=_values,
    validate_strings=True,
)
