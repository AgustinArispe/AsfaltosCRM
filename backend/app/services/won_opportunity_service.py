from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    Product,
    User,
)
from app.services.errors import RevisionConflictError
from app.services.opportunity_query_service import OpportunityQueryService


@dataclass(frozen=True, slots=True)
class WonFilters:
    search: str | None = None
    product_id: int | None = None
    source: LeadSource | None = None
    province: str | None = None
    assigned_user_id: int | None = None
    unassigned: bool = False
    won_from: datetime | None = None
    won_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class WonProjection:
    opportunity: Opportunity
    won_at: datetime
    won_total_kg: Decimal


@dataclass(frozen=True, slots=True)
class WonPage:
    items: tuple[WonProjection, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class WonStatistics:
    won_count: int
    won_quantity_kg: Decimal


@dataclass(frozen=True, slots=True)
class WonProductOption:
    id: int
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class WonUserOption:
    id: int
    full_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class WonFilterOptions:
    products: tuple[WonProductOption, ...]
    provinces: tuple[str, ...]
    responsible_users: tuple[WonUserOption, ...]


class WonOpportunityQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, filters: WonFilters, *, limit: int, cursor: str | None) -> WonPage:
        quantity = (
            select(func.coalesce(func.sum(OpportunityProduct.quantity_kg), 0))
            .where(OpportunityProduct.opportunity_id == Opportunity.id)
            .correlate(Opportunity)
            .scalar_subquery()
        )
        statement = select(
            Opportunity.id, Opportunity.current_status_entered_at, quantity
        ).where(*self._conditions(filters))
        if cursor:
            won_at, opportunity_id = _decode_cursor(cursor)
            statement = statement.where(
                or_(
                    Opportunity.current_status_entered_at < won_at,
                    (Opportunity.current_status_entered_at == won_at)
                    & (Opportunity.id < opportunity_id),
                )
            )
        rows = list(
            self._session.execute(
                statement.order_by(
                    Opportunity.current_status_entered_at.desc(), Opportunity.id.desc()
                ).limit(limit + 1)
            )
        )
        visible = rows[:limit]
        ids = [int(row[0]) for row in visible]
        opportunities = (
            {
                item.id: item
                for item in self._session.scalars(
                    select(Opportunity)
                    .where(Opportunity.id.in_(ids))
                    .options(*OpportunityQueryService._summary_load_options())
                ).unique()
            }
            if ids
            else {}
        )
        items = tuple(
            WonProjection(opportunities[int(row[0])], row[1], Decimal(row[2]))
            for row in visible
        )
        next_cursor = (
            _encode_cursor(items[-1].won_at, items[-1].opportunity.id)
            if len(rows) > limit and items
            else None
        )
        return WonPage(items, next_cursor)

    def statistics(self, filters: WonFilters) -> WonStatistics:
        matching = select(Opportunity.id).where(*self._conditions(filters)).subquery()
        count = self._session.scalar(select(func.count()).select_from(matching)) or 0
        quantity = self._session.scalar(
            select(func.coalesce(func.sum(OpportunityProduct.quantity_kg), 0)).join(
                matching, matching.c.id == OpportunityProduct.opportunity_id
            )
        )
        return WonStatistics(count, Decimal(quantity or 0))

    def filter_options(self) -> WonFilterOptions:
        base = (
            Opportunity.status == OpportunityStatus.GANADA,
            Opportunity.deleted_at.is_(None),
        )
        products = tuple(
            WonProductOption(*row)
            for row in self._session.execute(
                select(Product.id, Product.name, Product.is_active)
                .join(OpportunityProduct)
                .join(Opportunity)
                .where(*base)
                .group_by(Product.id, Product.name, Product.is_active)
                .order_by(func.lower(Product.name), Product.id)
            )
        )
        provinces = tuple(
            row[0]
            for row in self._session.execute(
                select(func.btrim(Customer.province))
                .join(Opportunity)
                .where(
                    *base,
                    Customer.province.is_not(None),
                    func.btrim(Customer.province) != "",
                )
                .group_by(func.btrim(Customer.province))
                .order_by(func.lower(func.btrim(Customer.province)))
            )
        )
        users = tuple(
            WonUserOption(*row)
            for row in self._session.execute(
                select(User.id, User.full_name, User.is_active)
                .join(Opportunity)
                .where(*base)
                .group_by(User.id, User.full_name, User.is_active)
                .order_by(func.lower(User.full_name), User.id)
            )
        )
        return WonFilterOptions(products, provinces, users)

    @staticmethod
    def _conditions(filters: WonFilters) -> tuple[ColumnElement[bool], ...]:
        conditions: list[ColumnElement[bool]] = [
            Opportunity.status == OpportunityStatus.GANADA,
            Opportunity.deleted_at.is_(None),
        ]
        if filters.search and (search := filters.search.strip()):
            pattern = f"%{search}%"
            values: list[ColumnElement[bool]] = [
                Customer.name.ilike(pattern),
                Customer.company.ilike(pattern),
            ]
            if search.isdigit():
                values.extend(
                    [
                        Opportunity.id == int(search),
                        Opportunity.customer_id == int(search),
                    ]
                )
            conditions.extend([Opportunity.customer_id == Customer.id, or_(*values)])
        if filters.product_id is not None:
            conditions.append(
                exists(
                    select(OpportunityProduct.opportunity_id).where(
                        OpportunityProduct.opportunity_id == Opportunity.id,
                        OpportunityProduct.product_id == filters.product_id,
                    )
                )
            )
        if filters.source is not None:
            conditions.append(Opportunity.source == filters.source)
        if filters.province and (province := filters.province.strip()):
            conditions.extend(
                [
                    Opportunity.customer_id == Customer.id,
                    func.lower(func.btrim(Customer.province)) == province.lower(),
                ]
            )
        if filters.assigned_user_id is not None:
            conditions.append(Opportunity.assigned_user_id == filters.assigned_user_id)
        if filters.unassigned:
            conditions.append(Opportunity.assigned_user_id.is_(None))
        if filters.won_from is not None:
            conditions.append(Opportunity.current_status_entered_at >= filters.won_from)
        if filters.won_to is not None:
            conditions.append(Opportunity.current_status_entered_at < filters.won_to)
        return tuple(conditions)


def _encode_cursor(won_at: datetime, opportunity_id: int) -> str:
    return (
        urlsafe_b64encode(f"{won_at.isoformat()}|{opportunity_id}".encode())
        .decode()
        .rstrip("=")
    )


def _decode_cursor(value: str) -> tuple[datetime, int]:
    try:
        raw = urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        timestamp, raw_id = raw.rsplit("|", 1)
        won_at = datetime.fromisoformat(timestamp)
        opportunity_id = int(raw_id)
    except (ValueError, UnicodeDecodeError) as error:
        raise RevisionConflictError("Invalid won-opportunity cursor") from error
    if won_at.tzinfo is None or opportunity_id <= 0:
        raise RevisionConflictError("Invalid won-opportunity cursor")
    return won_at, opportunity_id
