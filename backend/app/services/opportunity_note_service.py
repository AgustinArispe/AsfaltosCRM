from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.models import Opportunity, OpportunityNote, OpportunityNoteRevision, User
from app.services.errors import (
    EntityNotFoundError,
    IdempotencyConflictError,
    RevisionConflictError,
)

MAX_NOTE_CHARS = 20_000


@dataclass(frozen=True, slots=True)
class NoteRevisionProjection:
    id: int
    revision_number: int
    body: str
    is_pinned: bool
    actor_user_id: int
    actor_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NoteProjection:
    id: int
    opportunity_id: int
    author_user_id: int
    author_name: str
    created_at: datetime
    current_revision: NoteRevisionProjection


@dataclass(frozen=True, slots=True)
class NotePage:
    items: tuple[NoteProjection, ...]
    next_cursor: str | None


class OpportunityNoteService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        opportunity_id: int,
        *,
        command_id: UUID,
        body: str,
        is_pinned: bool,
        actor_user_id: int,
    ) -> NoteProjection:
        normalized_body = _normalize_body(body)
        with self._session.begin():
            replay = self._session.scalar(
                select(OpportunityNoteRevision)
                .where(OpportunityNoteRevision.command_id == command_id)
                .options(joinedload(OpportunityNoteRevision.note))
            )
            if replay is not None:
                if (
                    replay.note.opportunity_id != opportunity_id
                    or replay.revision_number != 1
                    or replay.body != normalized_body
                    or replay.is_pinned != is_pinned
                    or replay.actor_user_id != actor_user_id
                ):
                    raise IdempotencyConflictError(
                        "Note command ID was already used with different input"
                    )
                return self._project(replay.note, replay)
            opportunity = self._available_opportunity(opportunity_id, for_update=True)
            actor = self._actor(actor_user_id)
            note = OpportunityNote(
                opportunity_id=opportunity.id,
                author_user_id=actor.id,
            )
            self._session.add(note)
            self._session.flush()
            revision = OpportunityNoteRevision(
                note_id=note.id,
                revision_number=1,
                body=normalized_body,
                is_pinned=is_pinned,
                actor_user_id=actor.id,
                command_id=command_id,
            )
            self._session.add(revision)
            self._session.flush()
            return self._project(note, revision)

    def revise(
        self,
        opportunity_id: int,
        note_id: int,
        *,
        command_id: UUID,
        expected_revision: int,
        body: str | None,
        is_pinned: bool | None,
        actor_user_id: int,
    ) -> NoteProjection:
        normalized_body = _normalize_body(body) if body is not None else None
        with self._session.begin():
            replay = self._session.scalar(
                select(OpportunityNoteRevision)
                .where(OpportunityNoteRevision.command_id == command_id)
                .options(joinedload(OpportunityNoteRevision.note))
            )
            if replay is not None:
                if (
                    replay.note_id != note_id
                    or replay.note.opportunity_id != opportunity_id
                    or replay.actor_user_id != actor_user_id
                    or replay.revision_number != expected_revision + 1
                    or (normalized_body is not None and replay.body != normalized_body)
                    or (is_pinned is not None and replay.is_pinned != is_pinned)
                ):
                    raise IdempotencyConflictError(
                        "Note command ID was already used with different input"
                    )
                return self._project(replay.note, replay)
            self._available_opportunity(opportunity_id, for_update=True)
            note = self._session.scalar(
                select(OpportunityNote)
                .where(
                    OpportunityNote.id == note_id,
                    OpportunityNote.opportunity_id == opportunity_id,
                )
                .with_for_update()
            )
            if note is None:
                raise EntityNotFoundError("OpportunityNote", note_id)
            latest = self._latest_revision(note.id, for_update=True)
            if latest.revision_number != expected_revision:
                raise RevisionConflictError("Expected note revision is stale")
            next_body = normalized_body if normalized_body is not None else latest.body
            next_pin = is_pinned if is_pinned is not None else latest.is_pinned
            if next_body == latest.body and next_pin == latest.is_pinned:
                raise RevisionConflictError("Note revision must change body or pin")
            self._actor(actor_user_id)
            revision = OpportunityNoteRevision(
                note_id=note.id,
                revision_number=latest.revision_number + 1,
                body=next_body,
                is_pinned=next_pin,
                actor_user_id=actor_user_id,
                command_id=command_id,
            )
            self._session.add(revision)
            self._session.flush()
            return self._project(note, revision)

    def list_current(
        self,
        opportunity_id: int,
        *,
        search: str | None,
        pinned: bool | None,
        limit: int,
        cursor: str | None,
    ) -> NotePage:
        self._available_opportunity(opportunity_id, for_update=False)
        latest_numbers = (
            select(
                OpportunityNoteRevision.note_id,
                func.max(OpportunityNoteRevision.revision_number).label(
                    "latest_number"
                ),
            )
            .group_by(OpportunityNoteRevision.note_id)
            .subquery()
        )
        revision = aliased(OpportunityNoteRevision)
        statement = (
            select(OpportunityNote, revision)
            .join(latest_numbers, latest_numbers.c.note_id == OpportunityNote.id)
            .join(
                revision,
                and_(
                    revision.note_id == OpportunityNote.id,
                    revision.revision_number == latest_numbers.c.latest_number,
                ),
            )
            .where(OpportunityNote.opportunity_id == opportunity_id)
            .order_by(
                revision.is_pinned.desc(),
                revision.created_at.desc(),
                OpportunityNote.id.desc(),
            )
            .limit(limit + 1)
        )
        if pinned is not None:
            statement = statement.where(revision.is_pinned == pinned)
        normalized_search = search.strip() if search else ""
        if normalized_search:
            statement = statement.where(
                func.to_tsvector("simple", revision.body).op("@@")(
                    func.plainto_tsquery("simple", normalized_search)
                )
            )
        if cursor is not None:
            cursor_pin, cursor_time, cursor_id = _decode_cursor(cursor)
            same_group_after = or_(
                revision.created_at < cursor_time,
                and_(
                    revision.created_at == cursor_time,
                    OpportunityNote.id < cursor_id,
                ),
            )
            cursor_filter = and_(revision.is_pinned.is_(False), same_group_after)
            if cursor_pin:
                cursor_filter = or_(
                    revision.is_pinned.is_(False),
                    and_(revision.is_pinned.is_(True), same_group_after),
                )
            statement = statement.where(cursor_filter)
        rows = list(self._session.execute(statement).tuples())
        visible = rows[:limit]
        items = tuple(self._project(note, current) for note, current in visible)
        next_cursor = None
        if len(rows) > limit and visible:
            last_note, last_revision = visible[-1]
            next_cursor = _encode_cursor(
                last_revision.is_pinned,
                last_revision.created_at,
                last_note.id,
            )
        return NotePage(items=items, next_cursor=next_cursor)

    def list_revisions(
        self, opportunity_id: int, note_id: int
    ) -> tuple[NoteRevisionProjection, ...]:
        self._available_opportunity(opportunity_id, for_update=False)
        note = self._session.scalar(
            select(OpportunityNote).where(
                OpportunityNote.id == note_id,
                OpportunityNote.opportunity_id == opportunity_id,
            )
        )
        if note is None:
            raise EntityNotFoundError("OpportunityNote", note_id)
        revisions = self._session.scalars(
            select(OpportunityNoteRevision)
            .where(OpportunityNoteRevision.note_id == note.id)
            .order_by(OpportunityNoteRevision.revision_number)
        ).all()
        return tuple(self._project_revision(revision) for revision in revisions)

    def _available_opportunity(
        self, opportunity_id: int, *, for_update: bool
    ) -> Opportunity:
        statement = select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        opportunity = self._session.scalar(statement)
        if opportunity is None:
            raise EntityNotFoundError("Opportunity", opportunity_id)
        return opportunity

    def _actor(self, user_id: int) -> User:
        actor = self._session.get(User, user_id)
        if actor is None:
            raise EntityNotFoundError("User", user_id)
        return actor

    def _latest_revision(
        self, note_id: int, *, for_update: bool
    ) -> OpportunityNoteRevision:
        statement = (
            select(OpportunityNoteRevision)
            .where(OpportunityNoteRevision.note_id == note_id)
            .order_by(OpportunityNoteRevision.revision_number.desc())
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update()
        revision = self._session.scalar(statement)
        if revision is None:
            raise EntityNotFoundError("OpportunityNote", note_id)
        return revision

    def _project(
        self, note: OpportunityNote, revision: OpportunityNoteRevision
    ) -> NoteProjection:
        author = self._actor(note.author_user_id)
        return NoteProjection(
            id=note.id,
            opportunity_id=note.opportunity_id,
            author_user_id=note.author_user_id,
            author_name=author.full_name,
            created_at=note.created_at,
            current_revision=self._project_revision(revision),
        )

    def _project_revision(
        self, revision: OpportunityNoteRevision
    ) -> NoteRevisionProjection:
        actor = self._actor(revision.actor_user_id)
        return NoteRevisionProjection(
            id=revision.id,
            revision_number=revision.revision_number,
            body=revision.body,
            is_pinned=revision.is_pinned,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            created_at=revision.created_at,
        )


def _normalize_body(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise RevisionConflictError("Note body cannot be blank")
    if len(normalized) > MAX_NOTE_CHARS:
        raise RevisionConflictError("Note body is too long")
    return normalized


def _encode_cursor(is_pinned: bool, created_at: datetime, note_id: int) -> str:
    raw = f"{int(is_pinned)}|{created_at.isoformat()}|{note_id}".encode()
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[bool, datetime, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        pin, timestamp, note_id = urlsafe_b64decode(padded).decode().split("|", 2)
        parsed_time = datetime.fromisoformat(timestamp)
        parsed_id = int(note_id)
    except (ValueError, UnicodeDecodeError) as error:
        raise RevisionConflictError("Invalid note cursor") from error
    if pin not in {"0", "1"} or parsed_time.tzinfo is None or parsed_id <= 0:
        raise RevisionConflictError("Invalid note cursor")
    return pin == "1", parsed_time, parsed_id
