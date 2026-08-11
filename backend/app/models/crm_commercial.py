from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    CUSTOMER_IMPORT_ACTION_DB_ENUM,
    CUSTOMER_IMPORT_ISSUE_CODE_DB_ENUM,
    CUSTOMER_IMPORT_STATUS_DB_ENUM,
    LEAD_SOURCE_DB_ENUM,
    LEGENDARY_EVENT_TYPE_DB_ENUM,
    LOSS_REASON_DB_ENUM,
    OPPORTUNITY_STATUS_DB_ENUM,
    CustomerImportAction,
    CustomerImportIssueCode,
    CustomerImportStatus,
    LeadSource,
    LegendaryEventType,
    LossReason,
    OpportunityStatus,
)

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.opportunity_status_history import OpportunityStatusHistory
    from app.models.product import Product
    from app.models.user import User


class OpportunityNote(Base):
    __tablename__ = "opportunity_notes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    author_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="notes")
    author: Mapped[User] = relationship(foreign_keys=[author_user_id])
    revisions: Mapped[list[OpportunityNoteRevision]] = relationship(
        back_populates="note", order_by="OpportunityNoteRevision.revision_number"
    )


class OpportunityNoteRevision(Base):
    __tablename__ = "opportunity_note_revisions"
    __table_args__ = (
        UniqueConstraint("note_id", "revision_number", name="uq_note_revision"),
        CheckConstraint("revision_number > 0", name="ck_note_revision_positive"),
        CheckConstraint("btrim(body) <> ''", name="ck_note_revision_body_not_blank"),
        Index(
            "ix_note_revisions_search",
            text("to_tsvector('simple'::regconfig, body)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    note_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunity_notes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    actor_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    command_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    note: Mapped[OpportunityNote] = relationship(back_populates="revisions")
    actor: Mapped[User] = relationship(foreign_keys=[actor_user_id])


class CustomerLegendaryEvent(Base):
    __tablename__ = "customer_legendary_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[LegendaryEventType] = mapped_column(
        LEGENDARY_EVENT_TYPE_DB_ENUM, nullable=False
    )
    before_manual: Mapped[bool] = mapped_column(Boolean, nullable=False)
    after_manual: Mapped[bool] = mapped_column(Boolean, nullable=False)
    before_automatic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    after_automatic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    before_effective: Mapped[bool] = mapped_column(Boolean, nullable=False)
    after_effective: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_won_opportunity_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("opportunities.id", ondelete="RESTRICT")
    )
    first_won_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OpportunityLossEvent(Base):
    __tablename__ = "opportunity_loss_events"
    __table_args__ = (Index("ix_loss_events_workspace", "lost_at", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("opportunities.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    status_history_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunity_status_history.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    from_status: Mapped[OpportunityStatus] = mapped_column(
        OPPORTUNITY_STATUS_DB_ENUM, nullable=False
    )
    reason: Mapped[LossReason] = mapped_column(LOSS_REASON_DB_ENUM, nullable=False)
    source: Mapped[LeadSource] = mapped_column(LEAD_SOURCE_DB_ENUM, nullable=False)
    customer_display_name: Mapped[str] = mapped_column(Text, nullable=False)
    customer_province: Mapped[str | None] = mapped_column(Text)
    quoted_total_kg: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0")
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    lost_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    opportunity: Mapped[Opportunity] = relationship(back_populates="loss_events")
    status_history: Mapped[OpportunityStatusHistory] = relationship()
    product_snapshots: Mapped[list[OpportunityLossProductSnapshot]] = relationship(
        back_populates="loss_event",
        order_by="OpportunityLossProductSnapshot.product_id",
    )


class OpportunityLossProductSnapshot(Base):
    __tablename__ = "opportunity_loss_product_snapshots"
    __table_args__ = (
        UniqueConstraint("loss_event_id", "product_id", name="uq_loss_product"),
        CheckConstraint("quantity_kg > 0", name="ck_loss_product_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    loss_event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunity_loss_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)

    loss_event: Mapped[OpportunityLossEvent] = relationship(
        back_populates="product_snapshots"
    )
    product: Mapped[Product] = relationship()


class OpportunityReopenEvent(Base):
    __tablename__ = "opportunity_reopen_events"
    __table_args__ = (
        CheckConstraint("target_status = 'NEGOCIACION'", name="ck_reopen_target"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("opportunities.id", ondelete="RESTRICT"), nullable=False
    )
    loss_event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunity_loss_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status_history_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("opportunity_status_history.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    target_status: Mapped[OpportunityStatus] = mapped_column(
        OPPORTUNITY_STATUS_DB_ENUM, nullable=False
    )
    actor_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    command_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    reopened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="reopen_events")


class CustomerImportBatch(TimestampMixin, Base):
    __tablename__ = "customer_import_batches"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    client_import_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    file_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CustomerImportStatus] = mapped_column(
        CUSTOMER_IMPORT_STATUS_DB_ENUM, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actor_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    create_count: Mapped[int] = mapped_column(Integer, nullable=False)
    enrich_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False)
    commit_command_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True)
    committed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rows: Mapped[list[CustomerImportRow]] = relationship(
        back_populates="batch", order_by="CustomerImportRow.row_number"
    )
    results: Mapped[list[CustomerImportResult]] = relationship(back_populates="batch")


class CustomerImportRow(Base):
    __tablename__ = "customer_import_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_number", name="uq_import_row_number"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customer_import_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    phone_match_key: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    action: Mapped[CustomerImportAction] = mapped_column(
        CUSTOMER_IMPORT_ACTION_DB_ENUM, nullable=False
    )
    resolved_customer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT")
    )

    batch: Mapped[CustomerImportBatch] = relationship(back_populates="rows")
    issues: Mapped[list[CustomerImportIssue]] = relationship(
        back_populates="row", order_by="CustomerImportIssue.id"
    )


class CustomerImportIssue(Base):
    __tablename__ = "customer_import_issues"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    row_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customer_import_rows.id", ondelete="RESTRICT"),
        nullable=False,
    )
    field_name: Mapped[str | None] = mapped_column(Text)
    code: Mapped[CustomerImportIssueCode] = mapped_column(
        CUSTOMER_IMPORT_ISSUE_CODE_DB_ENUM, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    row: Mapped[CustomerImportRow] = relationship(back_populates="issues")


class CustomerImportResult(Base):
    __tablename__ = "customer_import_results"
    __table_args__ = (UniqueConstraint("row_id", name="uq_import_result_row"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customer_import_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    row_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customer_import_rows.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[CustomerImportAction] = mapped_column(
        CUSTOMER_IMPORT_ACTION_DB_ENUM, nullable=False
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    batch: Mapped[CustomerImportBatch] = relationship(back_populates="results")
