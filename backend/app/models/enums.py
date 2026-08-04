from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum


class UserRole(str, Enum):
    SUPERVISOR = "SUPERVISOR"
    VENDEDOR = "VENDEDOR"


class LeadSource(str, Enum):
    WEB = "WEB"
    WHATSAPP = "WHATSAPP"


class OpportunityStatus(str, Enum):
    NUEVA = "NUEVA"
    COTIZADA = "COTIZADA"
    NEGOCIACION = "NEGOCIACION"
    GANADA = "GANADA"
    PERDIDA = "PERDIDA"


class LossReason(str, Enum):
    PRECIO = "PRECIO"
    SIN_RESPUESTA = "SIN_RESPUESTA"
    COMPETENCIA = "COMPETENCIA"
    PROYECTO_CANCELADO = "PROYECTO_CANCELADO"
    OTRO = "OTRO"


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
