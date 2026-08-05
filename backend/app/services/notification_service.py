from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, exists, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    Notification,
    NotificationType,
    Opportunity,
    OpportunityStatus,
)
from app.models.enums import NOTIFICATION_TYPE_DB_ENUM
from app.services.errors import EntityNotFoundError

STALE_OPPORTUNITY_STATUSES = frozenset(
    {
        OpportunityStatus.NUEVA,
        OpportunityStatus.COTIZADA,
        OpportunityStatus.NEGOCIACION,
    }
)


class NotificationService:
    """Generates and manages global operational notifications."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def generate_stale_opportunity_notifications(
        self,
        *,
        now: datetime,
        threshold_days: int,
    ) -> int:
        generated_at = self._aware_utc(now)
        if threshold_days <= 0:
            raise ValueError("Stale opportunity threshold must be greater than zero")
        stale_before = generated_at - timedelta(days=threshold_days)

        active_notification_exists = exists(
            select(Notification.id).where(
                Notification.opportunity_id == Opportunity.id,
                Notification.type == NotificationType.OPPORTUNITY_STALE,
                Notification.resolved_at.is_(None),
            )
        )
        eligible_opportunities = select(
            literal(
                NotificationType.OPPORTUNITY_STALE,
                type_=NOTIFICATION_TYPE_DB_ENUM,
            ),
            Opportunity.id,
            literal(generated_at, type_=DateTime(timezone=True)),
        ).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.status.in_(STALE_OPPORTUNITY_STATUSES),
            Opportunity.current_status_entered_at <= stale_before,
            ~active_notification_exists,
        )

        with self._session.begin():
            created_ids = self._session.scalars(
                insert(Notification)
                .from_select(
                    ["type", "opportunity_id", "created_at"],
                    eligible_opportunities,
                )
                .on_conflict_do_nothing()
                .returning(Notification.id)
            )
            return len(created_ids.all())

    def list_notifications(
        self,
        *,
        page: int,
        page_size: int,
        unread_only: bool,
        include_resolved: bool,
    ) -> tuple[list[Notification], int]:
        filters: list[ColumnElement[bool]] = []
        if unread_only:
            filters.append(Notification.read_at.is_(None))
        if not include_resolved:
            filters.append(Notification.resolved_at.is_(None))

        total = self._session.scalar(
            select(func.count()).select_from(Notification).where(*filters)
        )
        notifications = list(
            self._session.scalars(
                select(Notification)
                .where(*filters)
                .options(
                    joinedload(Notification.opportunity).joinedload(
                        Opportunity.customer
                    )
                )
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return notifications, total or 0

    def get_notification(self, notification_id: int) -> Notification:
        notification = self._session.scalar(
            select(Notification)
            .where(Notification.id == notification_id)
            .options(
                joinedload(Notification.opportunity).joinedload(Opportunity.customer)
            )
        )
        if notification is None:
            raise EntityNotFoundError("Notification", notification_id)
        return notification

    def mark_as_read(
        self,
        notification_id: int,
        *,
        now: datetime,
    ) -> Notification:
        read_at = self._aware_utc(now)
        with self._session.begin():
            notification = self._session.scalar(
                select(Notification)
                .where(Notification.id == notification_id)
                .with_for_update()
            )
            if notification is None:
                raise EntityNotFoundError("Notification", notification_id)
            if notification.read_at is None:
                notification.read_at = read_at
                self._session.flush()
        return notification

    def mark_all_active_as_read(self, *, now: datetime) -> int:
        read_at = self._aware_utc(now)
        with self._session.begin():
            updated_ids = self._session.scalars(
                update(Notification)
                .where(
                    Notification.read_at.is_(None),
                    Notification.resolved_at.is_(None),
                )
                .values(read_at=read_at)
                .returning(Notification.id)
            )
            return len(updated_ids.all())

    def resolve_stale_for_opportunity_in_transaction(
        self,
        opportunity_id: int,
        *,
        resolved_at: datetime,
    ) -> None:
        """Resolve active stale notices inside a caller-owned transaction."""
        resolution_time = self._aware_utc(resolved_at)
        self._session.execute(
            update(Notification)
            .where(
                Notification.opportunity_id == opportunity_id,
                Notification.type == NotificationType.OPPORTUNITY_STALE,
                Notification.resolved_at.is_(None),
            )
            .values(resolved_at=resolution_time)
        )

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware")
        return value.astimezone(UTC)
