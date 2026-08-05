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
