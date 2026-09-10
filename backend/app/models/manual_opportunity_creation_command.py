from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ManualOpportunityCreationCommand(Base):
    __tablename__ = "manual_opportunity_creation_commands"

    command_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "opportunities.id",
            name="fk_manual_opportunity_commands_opportunity_id_opportunities",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_manual_opportunity_commands_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
