from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, exists, func, literal, select, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    Notification,
    NotificationRecipient,
    NotificationType,
    Opportunity,
    OpportunityStatus,
    User,
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


@dataclass(frozen=True, slots=True)
class UserNotification:
    id: int
    type: NotificationType
    created_at: datetime
    read_at: datetime | None
    resolved_at: datetime | None
    opportunity: Opportunity


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
            notification_ids = created_ids.all()
            self._create_recipients_in_transaction(notification_ids)
            return len(notification_ids)

    def create_new_lead_notification_in_transaction(
        self,
        opportunity: Opportunity,
        *,
        created_at: datetime,
    ) -> Notification:
        """Create one logical event and its active-user recipients in a transaction."""
        notification = Notification(
            type=NotificationType.NEW_LEAD,
            opportunity=opportunity,
            created_at=self._aware_utc(created_at),
        )
        self._session.add(notification)
        self._session.flush()
        self._create_recipients_in_transaction([notification.id])
        return notification

    def list_notifications(
        self,
        *,
        page: int,
        page_size: int,
        unread_only: bool,
        include_resolved: bool,
        current_user_id: int,
        notification_type: NotificationType | None = None,
    ) -> tuple[list[UserNotification], int]:
        filters: list[ColumnElement[bool]] = []
        if unread_only:
            filters.append(NotificationRecipient.read_at.is_(None))
        if not include_resolved:
            filters.append(Notification.resolved_at.is_(None))
        if notification_type is not None:
            filters.append(Notification.type == notification_type)

        total = self._session.scalar(
            select(func.count())
            .select_from(NotificationRecipient)
            .join(Notification)
            .where(NotificationRecipient.user_id == current_user_id, *filters)
        )
        rows = self._session.execute(
            select(Notification, NotificationRecipient.read_at)
            .join(NotificationRecipient)
            .where(NotificationRecipient.user_id == current_user_id, *filters)
            .options(
                joinedload(Notification.opportunity).joinedload(Opportunity.customer)
            )
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [
            self._delivery(notification, read_at) for notification, read_at in rows
        ], total or 0

    def get_notification(
        self,
        notification_id: int,
        *,
        current_user_id: int,
    ) -> UserNotification:
        row = self._session.execute(
            select(Notification, NotificationRecipient.read_at)
            .join(NotificationRecipient)
            .where(
                Notification.id == notification_id,
                NotificationRecipient.user_id == current_user_id,
            )
            .options(
                joinedload(Notification.opportunity).joinedload(Opportunity.customer)
            )
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Notification", notification_id)
        return self._delivery(*row)

    def mark_as_read(
        self,
        notification_id: int,
        *,
        current_user_id: int,
        now: datetime,
    ) -> UserNotification:
        read_at = self._aware_utc(now)
        with self._session.begin():
            recipient = self._session.scalar(
                select(NotificationRecipient)
                .where(
                    NotificationRecipient.notification_id == notification_id,
                    NotificationRecipient.user_id == current_user_id,
                )
                .options(
                    joinedload(NotificationRecipient.notification)
                    .joinedload(Notification.opportunity)
                    .joinedload(Opportunity.customer)
                )
                .with_for_update(of=NotificationRecipient)
            )
            if recipient is None:
                raise EntityNotFoundError("Notification", notification_id)
            if recipient.read_at is None:
                recipient.read_at = read_at
                self._session.flush()
            return self._delivery(recipient.notification, recipient.read_at)

    def mark_all_active_as_read(self, *, current_user_id: int, now: datetime) -> int:
        read_at = self._aware_utc(now)
        with self._session.begin():
            updated_ids = self._session.scalars(
                update(NotificationRecipient)
                .where(
                    NotificationRecipient.user_id == current_user_id,
                    NotificationRecipient.read_at.is_(None),
                    NotificationRecipient.notification_id.in_(
                        select(Notification.id).where(
                            Notification.resolved_at.is_(None)
                        )
                    ),
                )
                .values(read_at=read_at)
                .returning(NotificationRecipient.id)
            )
            return len(updated_ids.all())

    def _create_recipients_in_transaction(
        self,
        notification_ids: Sequence[int],
    ) -> None:
        for notification_id in notification_ids:
            recipients = (
                select(
                    Notification.id,
                    User.id,
                    Notification.created_at,
                )
                .select_from(Notification)
                .join(User, true())
                .where(
                    Notification.id == notification_id,
                    User.is_active.is_(True),
                )
            )
            self._session.execute(
                insert(NotificationRecipient)
                .from_select(["notification_id", "user_id", "created_at"], recipients)
                .on_conflict_do_nothing(
                    constraint="uq_notification_recipients_notification_user"
                )
            )

    @staticmethod
    def _delivery(
        notification: Notification,
        read_at: datetime | None,
    ) -> UserNotification:
        return UserNotification(
            id=notification.id,
            type=notification.type,
            created_at=notification.created_at,
            read_at=read_at,
            resolved_at=notification.resolved_at,
            opportunity=notification.opportunity,
        )

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
