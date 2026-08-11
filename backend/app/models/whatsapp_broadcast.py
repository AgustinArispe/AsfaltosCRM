from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    WHATSAPP_BROADCAST_AUDIT_EVENT_TYPE_DB_ENUM,
    WHATSAPP_BROADCAST_RECIPIENT_STATUS_DB_ENUM,
    WHATSAPP_BROADCAST_STATUS_DB_ENUM,
    WHATSAPP_MESSAGE_TYPE_DB_ENUM,
    WhatsAppBroadcastAuditEventType,
    WhatsAppBroadcastRecipientStatus,
    WhatsAppBroadcastStatus,
    WhatsAppMessageType,
)

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User
    from app.models.whatsapp_conversation import WhatsAppConversation
    from app.models.whatsapp_marketing_consent_event import (
        WhatsAppMarketingConsentEvent,
    )
    from app.models.whatsapp_message import WhatsAppMessage


class WhatsAppBroadcast(TimestampMixin, Base):
    __tablename__ = "whatsapp_broadcasts"
    __table_args__ = (
        CheckConstraint("btrim(label) <> ''", name="ck_whatsapp_broadcasts_label"),
        CheckConstraint("version > 0", name="ck_whatsapp_broadcasts_version_positive"),
        CheckConstraint(
            "btrim(template_external_id) <> '' AND btrim(template_name) <> '' "
            "AND btrim(template_language) <> ''",
            name="ck_whatsapp_broadcasts_template_identity",
        ),
        CheckConstraint(
            "header_media_ref IS NULL OR (header_media_storage_key IS NOT NULL "
            "AND header_media_mime_type IS NOT NULL "
            "AND header_media_size_bytes IS NOT NULL)",
            name="ck_whatsapp_broadcasts_header_media_complete",
        ),
        Index(
            "uq_whatsapp_broadcasts_client_generated_id",
            "client_generated_id",
            unique=True,
        ),
        Index("ix_whatsapp_broadcasts_status_id", "status", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    client_generated_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    external_campaign_reference: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WhatsAppBroadcastStatus] = mapped_column(
        WHATSAPP_BROADCAST_STATUS_DB_ENUM,
        nullable=False,
        default=WhatsAppBroadcastStatus.DRAFT,
        server_default=WhatsAppBroadcastStatus.DRAFT.value,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    template_external_id: Mapped[str] = mapped_column(Text, nullable=False)
    template_name: Mapped[str] = mapped_column(Text, nullable=False)
    template_language: Mapped[str] = mapped_column(Text, nullable=False)
    template_category: Mapped[str] = mapped_column(Text, nullable=False)
    template_provider_status: Mapped[str] = mapped_column(Text, nullable=False)
    template_header_type: Mapped[WhatsAppMessageType | None] = mapped_column(
        WHATSAPP_MESSAGE_TYPE_DB_ENUM
    )
    template_header_media_required: Mapped[bool] = mapped_column(nullable=False)
    template_component_signature: Mapped[str] = mapped_column(Text, nullable=False)
    header_media_ref: Mapped[UUID | None] = mapped_column(Uuid)
    header_media_storage_key: Mapped[str | None] = mapped_column(Text)
    header_media_mime_type: Mapped[str | None] = mapped_column(Text)
    header_media_filename: Mapped[str | None] = mapped_column(Text)
    header_media_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    header_media_sha256: Mapped[str | None] = mapped_column(Text)
    validation_token: Mapped[UUID | None] = mapped_column(Uuid)
    validation_digest: Mapped[str | None] = mapped_column(Text)
    validation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_whatsapp_broadcasts_created_by_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    confirmed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_whatsapp_broadcasts_confirmed_by_users",
            ondelete="RESTRICT",
        ),
    )
    started_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_whatsapp_broadcasts_started_by_users",
            ondelete="RESTRICT",
        ),
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    parameters: Mapped[list[WhatsAppBroadcastTemplateParameter]] = relationship(
        back_populates="broadcast",
        passive_deletes=True,
        order_by=lambda: WhatsAppBroadcastTemplateParameter.position,
    )
    recipients: Mapped[list[WhatsAppBroadcastRecipient]] = relationship(
        back_populates="broadcast",
        passive_deletes=True,
        order_by=lambda: WhatsAppBroadcastRecipient.id,
    )
    audit_events: Mapped[list[WhatsAppBroadcastAuditEvent]] = relationship(
        back_populates="broadcast",
        passive_deletes=True,
        order_by=lambda: WhatsAppBroadcastAuditEvent.id,
    )


class WhatsAppBroadcastTemplateParameter(Base):
    __tablename__ = "whatsapp_broadcast_template_parameters"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_whatsapp_broadcast_params_position"),
        CheckConstraint(
            "btrim(name) <> '' AND btrim(value) <> ''",
            name="ck_whatsapp_broadcast_params_nonblank",
        ),
        UniqueConstraint(
            "broadcast_id",
            "name",
            name="uq_whatsapp_broadcast_params_name",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_broadcasts.id",
            name="fk_whatsapp_broadcast_params_broadcasts",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    broadcast: Mapped[WhatsAppBroadcast] = relationship(
        back_populates="parameters",
        passive_deletes=True,
    )


class WhatsAppBroadcastRecipient(TimestampMixin, Base):
    __tablename__ = "whatsapp_broadcast_recipients"
    __table_args__ = (
        CheckConstraint(
            "btrim(normalized_phone) <> ''",
            name="ck_whatsapp_broadcast_recipients_phone",
        ),
        UniqueConstraint(
            "broadcast_id",
            "normalized_phone",
            name="uq_whatsapp_broadcast_recipients_phone",
        ),
        Index("ix_whatsapp_broadcast_recipients_claim", "broadcast_id", "status", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_broadcasts.id",
            name="fk_whatsapp_broadcast_recipients_broadcasts",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "customers.id",
            name="fk_whatsapp_broadcast_recipients_customers",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    customer_display_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_phone: Mapped[str] = mapped_column(Text, nullable=False)
    consent_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_marketing_consent_events.id",
            name="fk_whatsapp_broadcast_recipients_consent_events",
            ondelete="RESTRICT",
        ),
    )
    status: Mapped[WhatsAppBroadcastRecipientStatus] = mapped_column(
        WHATSAPP_BROADCAST_RECIPIENT_STATUS_DB_ENUM,
        nullable=False,
        default=WhatsAppBroadcastRecipientStatus.DRAFT,
        server_default=WhatsAppBroadcastRecipientStatus.DRAFT.value,
    )
    reason_code: Mapped[str | None] = mapped_column(Text)
    safe_error_code: Mapped[str | None] = mapped_column(Text)
    safe_error_message: Mapped[str | None] = mapped_column(Text)
    conversation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_conversations.id",
            name="fk_whatsapp_broadcast_recipients_conversations",
            ondelete="RESTRICT",
        ),
    )
    claim_token: Mapped[UUID | None] = mapped_column(Uuid)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    broadcast: Mapped[WhatsAppBroadcast] = relationship(
        back_populates="recipients",
        passive_deletes=True,
    )
    customer: Mapped[Customer] = relationship(passive_deletes=True)
    consent_event: Mapped[WhatsAppMarketingConsentEvent | None] = relationship(
        passive_deletes=True
    )
    conversation: Mapped[WhatsAppConversation | None] = relationship(
        passive_deletes=True
    )
    messages: Mapped[list[WhatsAppMessage]] = relationship(
        back_populates="broadcast_recipient",
        passive_deletes=True,
        order_by="WhatsAppMessage.id",
    )


class WhatsAppBroadcastAuditEvent(Base):
    __tablename__ = "whatsapp_broadcast_audit_events"
    __table_args__ = (
        Index(
            "uq_whatsapp_broadcast_audit_command",
            "broadcast_id",
            "command_id",
            unique=True,
            postgresql_where=text("command_id IS NOT NULL"),
        ),
        Index("ix_whatsapp_broadcast_audit_broadcast", "broadcast_id", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_broadcasts.id",
            name="fk_whatsapp_broadcast_audit_broadcasts",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    recipient_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_broadcast_recipients.id",
            name="fk_whatsapp_broadcast_audit_recipients",
            ondelete="RESTRICT",
        ),
    )
    message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "whatsapp_messages.id",
            name="fk_whatsapp_broadcast_audit_messages",
            ondelete="RESTRICT",
        ),
    )
    command_id: Mapped[UUID | None] = mapped_column(Uuid)
    event_type: Mapped[WhatsAppBroadcastAuditEventType] = mapped_column(
        WHATSAPP_BROADCAST_AUDIT_EVENT_TYPE_DB_ENUM,
        nullable=False,
    )
    reason_code: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id",
            name="fk_whatsapp_broadcast_audit_actor_users",
            ondelete="RESTRICT",
        ),
    )
    affected_count: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    broadcast: Mapped[WhatsAppBroadcast] = relationship(
        back_populates="audit_events",
        passive_deletes=True,
    )
    actor_user: Mapped[User | None] = relationship(passive_deletes=True)
