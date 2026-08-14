from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.whatsapp_message import WhatsAppMessage


class WhatsAppHumanTemplateParameter(Base):
    __tablename__ = "whatsapp_human_template_parameters"
    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="ck_whatsapp_human_template_params_position",
        ),
        CheckConstraint(
            "btrim(name) <> '' AND btrim(value) <> ''",
            name="ck_whatsapp_human_template_params_nonblank",
        ),
        UniqueConstraint(
            "message_id",
            "name",
            name="uq_whatsapp_human_template_params_message_name",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_messages.id",
            name="fk_whatsapp_human_template_params_message_id_messages",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    message: Mapped[WhatsAppMessage] = relationship(
        back_populates="human_template_parameters",
        passive_deletes=True,
    )
