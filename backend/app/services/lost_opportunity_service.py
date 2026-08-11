from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    LeadSource,
    LossReason,
    Opportunity,
    OpportunityLossEvent,
    OpportunityLossProductSnapshot,
    OpportunityReopenEvent,
    OpportunityStatus,
)
from app.services.errors import RevisionConflictError
from app.services.opportunity_query_service import OpportunityQueryService

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


@dataclass(frozen=True, slots=True)
class LostFilters:
    search: str | None = None
    reasons: tuple[LossReason, ...] = ()
    customer_id: int | None = None
    province: str | None = None
    product_id: int | None = None
    source: LeadSource | None = None
    lost_from: datetime | None = None
    lost_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class LostProjection:
    opportunity: Opportunity
    loss_event_id: int
    loss_reason: LossReason
    lost_at: datetime
    quoted_total_kg: Decimal
    loss_products: tuple[OpportunityLossProductSnapshot, ...]


@dataclass(frozen=True, slots=True)
class LostPage:
    items: tuple[LostProjection, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class StatisticBucket:
    key: str
    count: int
    quantity_kg: Decimal


@dataclass(frozen=True, slots=True)
class ProductStatisticBucket:
    product_id: int
    product_name: str
    count: int
    quantity_kg: Decimal


@dataclass(frozen=True, slots=True)
class LostStatistics:
    current_count: int
    current_quantity_kg: Decimal
    historical_loss_count: int
    historical_quantity_kg: Decimal
    reopened_count: int
    by_reason: tuple[StatisticBucket, ...]
    by_product: tuple[ProductStatisticBucket, ...]
    by_source: tuple[StatisticBucket, ...]
    by_province: tuple[StatisticBucket, ...]
    timeline: tuple[StatisticBucket, ...]


class LostOpportunityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_current(
        self,
        filters: LostFilters,
        *,
        limit: int,
        cursor: str | None,
    ) -> LostPage:
        latest = (
            select(
                OpportunityLossEvent.opportunity_id,
                func.max(OpportunityLossEvent.id).label("event_id"),
            )
            .group_by(OpportunityLossEvent.opportunity_id)
            .subquery()
        )
        statement = (
            select(OpportunityLossEvent)
            .join(latest, latest.c.event_id == OpportunityLossEvent.id)
            .join(Opportunity, Opportunity.id == OpportunityLossEvent.opportunity_id)
            .where(
                Opportunity.status == OpportunityStatus.PERDIDA,
                Opportunity.deleted_at.is_(None),
            )
            .options(selectinload(OpportunityLossEvent.product_snapshots))
            .order_by(
                OpportunityLossEvent.lost_at.desc(), OpportunityLossEvent.id.desc()
            )
            .limit(limit + 1)
        )
        statement = statement.where(*self._conditions(filters))
        if cursor:
            lost_at, event_id = _decode_cursor(cursor)
            statement = statement.where(
                or_(
                    OpportunityLossEvent.lost_at < lost_at,
                    (
                        (OpportunityLossEvent.lost_at == lost_at)
                        & (OpportunityLossEvent.id < event_id)
                    ),
                )
            )
        events = list(self._session.scalars(statement).unique())
        visible = events[:limit]
        query_service = OpportunityQueryService(self._session)
        items = tuple(
            LostProjection(
                opportunity=query_service.get_detail(event.opportunity_id),
                loss_event_id=event.id,
                loss_reason=event.reason,
                lost_at=event.lost_at,
                quoted_total_kg=event.quoted_total_kg,
                loss_products=tuple(event.product_snapshots),
            )
            for event in visible
        )
        next_cursor = None
        if len(events) > limit and visible:
            last = visible[-1]
            next_cursor = _encode_cursor(last.lost_at, last.id)
        return LostPage(items=items, next_cursor=next_cursor)

    def statistics(self, filters: LostFilters) -> LostStatistics:
        events = list(
            self._session.scalars(
                select(OpportunityLossEvent)
                .where(*self._conditions(filters))
                .options(selectinload(OpportunityLossEvent.product_snapshots))
                .order_by(OpportunityLossEvent.id)
            ).unique()
        )
        current_event_ids = set(
            self._session.scalars(
                select(func.max(OpportunityLossEvent.id))
                .join(Opportunity)
                .where(
                    Opportunity.status == OpportunityStatus.PERDIDA,
                    Opportunity.deleted_at.is_(None),
                )
                .group_by(OpportunityLossEvent.opportunity_id)
            )
        )
        filtered_ids = {event.id for event in events}
        current = [event for event in events if event.id in current_event_ids]
        reopened_ids = (
            set(
                self._session.scalars(
                    select(OpportunityReopenEvent.loss_event_id).where(
                        OpportunityReopenEvent.loss_event_id.in_(filtered_ids)
                    )
                )
            )
            if filtered_ids
            else set()
        )
        return LostStatistics(
            current_count=len(current),
            current_quantity_kg=sum(
                (event.quoted_total_kg for event in current), Decimal("0")
            ),
            historical_loss_count=len(events),
            historical_quantity_kg=sum(
                (event.quoted_total_kg for event in events), Decimal("0")
            ),
            reopened_count=len(reopened_ids),
            by_reason=_event_buckets(events, lambda event: event.reason.value),
            by_product=_product_buckets(events),
            by_source=_event_buckets(events, lambda event: event.source.value),
            by_province=_event_buckets(
                events, lambda event: event.customer_province or "<NONE>"
            ),
            timeline=_event_buckets(
                events,
                lambda event: event.lost_at.astimezone(BUENOS_AIRES).date().isoformat(),
            ),
        )

    @staticmethod
    def _conditions(filters: LostFilters) -> tuple[ColumnElement[bool], ...]:
        conditions: list[ColumnElement[bool]] = []
        if filters.search:
            search = filters.search.strip()
            if search:
                pattern = f"%{search}%"
                numeric_id = int(search) if search.isdigit() else None
                search_conditions: list[ColumnElement[bool]] = [
                    OpportunityLossEvent.customer_display_name.ilike(pattern)
                ]
                if numeric_id is not None:
                    search_conditions.extend(
                        [
                            OpportunityLossEvent.opportunity_id == numeric_id,
                            OpportunityLossEvent.customer_id == numeric_id,
                        ]
                    )
                conditions.append(or_(*search_conditions))
        if filters.reasons:
            conditions.append(OpportunityLossEvent.reason.in_(filters.reasons))
        if filters.customer_id is not None:
            conditions.append(OpportunityLossEvent.customer_id == filters.customer_id)
        if filters.province:
            conditions.append(
                func.lower(func.btrim(OpportunityLossEvent.customer_province))
                == filters.province.strip().lower()
            )
        if filters.product_id is not None:
            conditions.append(
                exists(
                    select(OpportunityLossProductSnapshot.id).where(
                        OpportunityLossProductSnapshot.loss_event_id
                        == OpportunityLossEvent.id,
                        OpportunityLossProductSnapshot.product_id == filters.product_id,
                    )
                )
            )
        if filters.source is not None:
            conditions.append(OpportunityLossEvent.source == filters.source)
        if filters.lost_from is not None:
            _require_aware(filters.lost_from)
            conditions.append(OpportunityLossEvent.lost_at >= filters.lost_from)
        if filters.lost_to is not None:
            _require_aware(filters.lost_to)
            conditions.append(OpportunityLossEvent.lost_at < filters.lost_to)
        return tuple(conditions)


def _event_buckets(
    events: list[OpportunityLossEvent],
    key_for: Callable[[OpportunityLossEvent], str],
) -> tuple[StatisticBucket, ...]:
    values: dict[str, tuple[int, Decimal]] = {}
    for event in events:
        key = key_for(event)
        count, quantity = values.get(key, (0, Decimal("0")))
        values[key] = count + 1, quantity + event.quoted_total_kg
    return tuple(
        StatisticBucket(key=key, count=count, quantity_kg=quantity)
        for key, (count, quantity) in sorted(values.items())
    )


def _product_buckets(
    events: list[OpportunityLossEvent],
) -> tuple[ProductStatisticBucket, ...]:
    values: dict[int, tuple[str, int, Decimal]] = {}
    for event in events:
        for product in event.product_snapshots:
            name, count, quantity = values.get(
                product.product_id, (product.product_name, 0, Decimal("0"))
            )
            values[product.product_id] = (
                name,
                count + 1,
                quantity + product.quantity_kg,
            )
    return tuple(
        ProductStatisticBucket(
            product_id=product_id,
            product_name=name,
            count=count,
            quantity_kg=quantity,
        )
        for product_id, (name, count, quantity) in sorted(values.items())
    )


def _encode_cursor(lost_at: datetime, event_id: int) -> str:
    return (
        urlsafe_b64encode(f"{lost_at.isoformat()}|{event_id}".encode())
        .decode()
        .rstrip("=")
    )


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        timestamp, event_id = urlsafe_b64decode(padded).decode().split("|", 1)
        lost_at = datetime.fromisoformat(timestamp)
        parsed_id = int(event_id)
    except (ValueError, UnicodeDecodeError) as error:
        raise RevisionConflictError("Invalid lost workspace cursor") from error
    if lost_at.tzinfo is None or lost_at.utcoffset() is None or parsed_id <= 0:
        raise RevisionConflictError("Invalid lost workspace cursor")
    return lost_at, parsed_id


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
