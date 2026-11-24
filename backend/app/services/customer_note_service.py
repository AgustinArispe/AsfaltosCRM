from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Customer, CustomerNote
from app.services.customer_identity_service import acquire_advisory_locks
from app.services.customer_service import CustomerService
from app.services.errors import (
    EntityNotFoundError,
    IdempotencyConflictError,
    InvalidTransitionNoteError,
    RevisionConflictError,
    StaleWriteConflictError,
)


class CustomerNoteService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_notes(
        self, customer_id: int, *, page: int, page_size: int
    ) -> tuple[list[CustomerNote], int]:
        CustomerService(self._session).get_customer(customer_id)
        filters = (
            CustomerNote.customer_id == customer_id,
            CustomerNote.archived_at.is_(None),
        )
        total = (
            self._session.scalar(
                select(func.count()).select_from(CustomerNote).where(*filters)
            )
            or 0
        )
        notes = self._session.scalars(
            select(CustomerNote)
            .options(joinedload(CustomerNote.author))
            .where(*filters)
            .order_by(CustomerNote.pinned.desc(), CustomerNote.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(notes), total

    def create(
        self, customer_id: int, *, body: str, actor_id: int, command_id: UUID
    ) -> CustomerNote:
        with self._session.begin():
            acquire_advisory_locks(
                self._session, (("customer-note-command", str(command_id)),)
            )
            self._lock_customer(customer_id)
            current = self._session.scalar(
                select(CustomerNote).where(CustomerNote.command_id == command_id)
            )
            if current is not None:
                if (
                    current.customer_id != customer_id
                    or current.author_user_id != actor_id
                    or current.body != body
                    or current.archived_at is not None
                ):
                    raise IdempotencyConflictError(
                        "Customer note command was already used"
                    )
                return current
            note = self.create_in_transaction(
                customer_id, body=body, actor_id=actor_id, command_id=command_id
            )
            self._session.flush()
        return note

    def create_in_transaction(
        self,
        customer_id: int,
        *,
        body: str,
        actor_id: int,
        command_id: UUID | None = None,
    ) -> CustomerNote:
        """Add a note while the caller holds the customer lock."""
        normalized = body.strip()
        if not normalized or len(normalized) > 600:
            raise InvalidTransitionNoteError(
                "Customer notes require 1 to 600 characters"
            )
        note = CustomerNote(
            customer_id=customer_id,
            body=normalized,
            author_user_id=actor_id,
            command_id=command_id,
        )
        self._session.add(note)
        return note

    def update(
        self,
        customer_id: int,
        note_id: int,
        *,
        body: str,
        pinned: bool,
        expected_updated_at: datetime,
    ) -> CustomerNote:
        with self._session.begin():
            self._lock_customer(customer_id)
            note = self._get_note(customer_id, note_id)
            if note.updated_at != expected_updated_at:
                raise StaleWriteConflictError(
                    resource="Customer note", current_updated_at=note.updated_at
                )
            if pinned and not note.pinned:
                count = (
                    self._session.scalar(
                        select(func.count())
                        .select_from(CustomerNote)
                        .where(
                            CustomerNote.customer_id == customer_id,
                            CustomerNote.pinned.is_(True),
                            CustomerNote.archived_at.is_(None),
                        )
                    )
                    or 0
                )
                if count >= 3:
                    raise RevisionConflictError(
                        "Only three notes can be pinned per customer"
                    )
            note.body = body
            note.pinned = pinned
            note.updated_at = datetime.now(UTC)
            self._session.flush()
        return note

    def archive(self, customer_id: int, note_id: int) -> None:
        with self._session.begin():
            self._lock_customer(customer_id)
            note = self._get_note(customer_id, note_id)
            note.archived_at = datetime.now(UTC)

    def _get_note(self, customer_id: int, note_id: int) -> CustomerNote:
        note = self._session.scalar(
            select(CustomerNote).where(
                CustomerNote.id == note_id,
                CustomerNote.customer_id == customer_id,
                CustomerNote.archived_at.is_(None),
            )
        )
        if note is None:
            raise EntityNotFoundError("Customer note", note_id)
        return note

    def _lock_customer(self, customer_id: int) -> None:
        found = self._session.scalar(
            select(Customer.id)
            .where(
                Customer.id == customer_id,
                Customer.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if found is None:
            raise EntityNotFoundError("Customer", customer_id)
