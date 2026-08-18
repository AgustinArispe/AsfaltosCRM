from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from sqlalchemy import Date, SQLColumnExpression, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    Product,
)
from app.services.errors import MetricsTimelinePeriodTooLargeError

BUSINESS_TIMEZONE_NAME = "America/Argentina/Buenos_Aires"
BUSINESS_TIMEZONE = ZoneInfo(BUSINESS_TIMEZONE_NAME)
OPEN_OPPORTUNITY_STATUSES = frozenset(
    {
        OpportunityStatus.NUEVA,
        OpportunityStatus.COTIZADA,
        OpportunityStatus.NEGOCIACION,
    }
)
QUOTED_OPEN_STATUSES = frozenset(
    {OpportunityStatus.COTIZADA, OpportunityStatus.NEGOCIACION}
)
TERMINAL_OPPORTUNITY_STATUSES = frozenset(
    {OpportunityStatus.GANADA, OpportunityStatus.PERDIDA}
)
ZERO_KG = Decimal("0.000")
RATIO_QUANTUM = Decimal("0.0001")
MAX_DAY_TIMELINE_BUCKETS = 366
MAX_MONTH_TIMELINE_BUCKETS = 1_200


class TimelineGranularity(StrEnum):
    DAY = "day"
    MONTH = "month"


class TimelineOpportunitySeries(StrEnum):
    CREATED = "created"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class MetricsPeriod:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if (
            self.start.tzinfo is None
            or self.start.utcoffset() is None
            or self.end.tzinfo is None
            or self.end.utcoffset() is None
        ):
            raise ValueError("Metrics period datetimes must be timezone-aware")
        if self.start >= self.end:
            raise ValueError("Metrics period start must be before end")


@dataclass(frozen=True, slots=True)
class MetricsDimensions:
    source: LeadSource | None = None
    product_id: int | None = None
    province: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsFilters:
    period: MetricsPeriod
    dimensions: MetricsDimensions


@dataclass(frozen=True, slots=True)
class OpportunityOverview:
    created: int
    won: int
    lost: int
    open: int
    conversion_rate: Decimal | None


@dataclass(frozen=True, slots=True)
class VolumeOverview:
    quoted: Decimal
    won: Decimal
    lost: Decimal
    open: Decimal
    conversion_rate: Decimal | None


@dataclass(frozen=True, slots=True)
class OverviewMetrics:
    opportunities: OpportunityOverview
    volume_kg: VolumeOverview


@dataclass(frozen=True, slots=True)
class ProductMetrics:
    product_id: int
    product_name: str
    opportunities_quoted: int
    kg_quoted: Decimal
    opportunities_won: int
    kg_won: Decimal
    opportunities_lost: int
    kg_lost: Decimal
    conversion_rate_opportunities: Decimal | None
    conversion_rate_kg: Decimal | None


@dataclass(frozen=True, slots=True)
class SourceMetrics:
    source: LeadSource
    created: int
    won: int
    lost: int
    conversion_rate: Decimal | None


@dataclass(frozen=True, slots=True)
class ProvinceMetrics:
    province: str | None
    opportunities_created: int
    opportunities_won: int
    opportunities_lost: int
    conversion_rate: Decimal | None
    kg_quoted: Decimal
    kg_won: Decimal
    kg_lost: Decimal


@dataclass(frozen=True, slots=True)
class TimelineBucket:
    bucket: date
    leads_created: int
    won: int
    lost: int
    kg_won: Decimal
    kg_lost: Decimal


@dataclass(frozen=True, slots=True)
class PipelineStatusMetrics:
    status: OpportunityStatus
    count: int


def conversion_rate(
    numerator: int | Decimal,
    denominator: int | Decimal,
) -> Decimal | None:
    if denominator == 0:
        return None
    decimal_numerator = (
        numerator if isinstance(numerator, Decimal) else Decimal(numerator)
    )
    decimal_denominator = (
        denominator if isinstance(denominator, Decimal) else Decimal(denominator)
    )
    return (decimal_numerator / decimal_denominator).quantize(
        RATIO_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


class MetricsService:
    """Calculates commercial metrics with aggregate PostgreSQL queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def overview(self, filters: MetricsFilters) -> OverviewMetrics:
        period = filters.period
        base_filters = self._opportunity_filters(filters.dimensions)
        created_in_period = self._in_period(Opportunity.created_at, period)
        closed_in_period = self._in_period(
            Opportunity.current_status_entered_at,
            period,
        )
        opportunity_statement = select(
            func.count(Opportunity.id).filter(created_in_period),
            func.count(Opportunity.id).filter(
                Opportunity.status == OpportunityStatus.GANADA,
                closed_in_period,
            ),
            func.count(Opportunity.id).filter(
                Opportunity.status == OpportunityStatus.PERDIDA,
                closed_in_period,
            ),
            func.count(Opportunity.id).filter(
                Opportunity.status.in_(OPEN_OPPORTUNITY_STATUSES),
                created_in_period,
            ),
        ).select_from(Opportunity)
        if filters.dimensions.province is not None:
            opportunity_statement = opportunity_statement.join(Customer)
        created, won, lost, open_count = self._session.execute(
            opportunity_statement.where(*base_filters)
        ).one()

        volume_filters = self._line_filters(filters.dimensions)
        volume_statement = (
            select(
                func.sum(OpportunityProduct.quantity_kg).filter(created_in_period),
                func.sum(OpportunityProduct.quantity_kg).filter(
                    Opportunity.status == OpportunityStatus.GANADA,
                    closed_in_period,
                ),
                func.sum(OpportunityProduct.quantity_kg).filter(
                    Opportunity.status == OpportunityStatus.PERDIDA,
                    closed_in_period,
                ),
                func.sum(OpportunityProduct.quantity_kg).filter(
                    Opportunity.status.in_(QUOTED_OPEN_STATUSES),
                    created_in_period,
                ),
            )
            .select_from(OpportunityProduct)
            .join(Opportunity)
        )
        if filters.dimensions.province is not None:
            volume_statement = volume_statement.join(Customer)
        quoted_kg, won_kg, lost_kg, open_kg = self._session.execute(
            volume_statement.where(*volume_filters)
        ).one()

        won_value = self._kg(won_kg)
        lost_value = self._kg(lost_kg)
        return OverviewMetrics(
            opportunities=OpportunityOverview(
                created=created,
                won=won,
                lost=lost,
                open=open_count,
                conversion_rate=conversion_rate(won, won + lost),
            ),
            volume_kg=VolumeOverview(
                quoted=self._kg(quoted_kg),
                won=won_value,
                lost=lost_value,
                open=self._kg(open_kg),
                conversion_rate=conversion_rate(
                    won_value,
                    won_value + lost_value,
                ),
            ),
        )

    def products(self, filters: MetricsFilters) -> list[ProductMetrics]:
        period = filters.period
        created_in_period = self._in_period(Opportunity.created_at, period)
        closed_in_period = self._in_period(
            Opportunity.current_status_entered_at,
            period,
        )
        won_in_period = and_(
            Opportunity.status == OpportunityStatus.GANADA,
            closed_in_period,
        )
        lost_in_period = and_(
            Opportunity.status == OpportunityStatus.PERDIDA,
            closed_in_period,
        )
        filters_sql = self._line_filters(filters.dimensions)
        statement = (
            select(
                Product.id,
                Product.name,
                func.count(func.distinct(Opportunity.id)).filter(created_in_period),
                func.sum(OpportunityProduct.quantity_kg).filter(created_in_period),
                func.count(func.distinct(Opportunity.id)).filter(won_in_period),
                func.sum(OpportunityProduct.quantity_kg).filter(won_in_period),
                func.count(func.distinct(Opportunity.id)).filter(lost_in_period),
                func.sum(OpportunityProduct.quantity_kg).filter(lost_in_period),
            )
            .select_from(OpportunityProduct)
            .join(Product)
            .join(Opportunity)
        )
        if filters.dimensions.province is not None:
            statement = statement.join(Customer)
        rows = self._session.execute(
            statement.where(
                *filters_sql,
                or_(created_in_period, won_in_period, lost_in_period),
            )
            .group_by(Product.id, Product.name)
            .order_by(
                func.coalesce(
                    func.sum(OpportunityProduct.quantity_kg).filter(created_in_period),
                    ZERO_KG,
                ).desc(),
                Product.id,
            )
        ).all()

        metrics: list[ProductMetrics] = []
        for row in rows:
            won_kg = self._kg(row[5])
            lost_kg = self._kg(row[7])
            metrics.append(
                ProductMetrics(
                    product_id=row[0],
                    product_name=row[1],
                    opportunities_quoted=row[2],
                    kg_quoted=self._kg(row[3]),
                    opportunities_won=row[4],
                    kg_won=won_kg,
                    opportunities_lost=row[6],
                    kg_lost=lost_kg,
                    conversion_rate_opportunities=conversion_rate(
                        row[4],
                        row[4] + row[6],
                    ),
                    conversion_rate_kg=conversion_rate(
                        won_kg,
                        won_kg + lost_kg,
                    ),
                )
            )
        return metrics

    def sources(self, filters: MetricsFilters) -> list[SourceMetrics]:
        period = filters.period
        created_in_period = self._in_period(Opportunity.created_at, period)
        closed_in_period = self._in_period(
            Opportunity.current_status_entered_at,
            period,
        )
        won_in_period = and_(
            Opportunity.status == OpportunityStatus.GANADA,
            closed_in_period,
        )
        lost_in_period = and_(
            Opportunity.status == OpportunityStatus.PERDIDA,
            closed_in_period,
        )
        statement = select(
            Opportunity.source,
            func.count(Opportunity.id).filter(created_in_period),
            func.count(Opportunity.id).filter(won_in_period),
            func.count(Opportunity.id).filter(lost_in_period),
        ).select_from(Opportunity)
        if filters.dimensions.province is not None:
            statement = statement.join(Customer)
        rows = self._session.execute(
            statement.where(
                *self._opportunity_filters(filters.dimensions),
                or_(created_in_period, won_in_period, lost_in_period),
            )
            .group_by(Opportunity.source)
            .order_by(Opportunity.source)
        ).all()
        return [
            SourceMetrics(
                source=row[0],
                created=row[1],
                won=row[2],
                lost=row[3],
                conversion_rate=conversion_rate(row[2], row[2] + row[3]),
            )
            for row in rows
        ]

    def provinces(self, filters: MetricsFilters) -> list[ProvinceMetrics]:
        period = filters.period
        line_totals = self._line_totals(filters.dimensions)
        created_in_period = self._in_period(Opportunity.created_at, period)
        closed_in_period = self._in_period(
            Opportunity.current_status_entered_at,
            period,
        )
        won_in_period = and_(
            Opportunity.status == OpportunityStatus.GANADA,
            closed_in_period,
        )
        lost_in_period = and_(
            Opportunity.status == OpportunityStatus.PERDIDA,
            closed_in_period,
        )
        rows = self._session.execute(
            select(
                Customer.province,
                func.count(Opportunity.id).filter(created_in_period),
                func.count(Opportunity.id).filter(won_in_period),
                func.count(Opportunity.id).filter(lost_in_period),
                func.sum(line_totals.c.total_kg).filter(created_in_period),
                func.sum(line_totals.c.total_kg).filter(won_in_period),
                func.sum(line_totals.c.total_kg).filter(lost_in_period),
            )
            .select_from(Opportunity)
            .join(Customer)
            .outerjoin(line_totals, line_totals.c.opportunity_id == Opportunity.id)
            .where(
                *self._opportunity_filters(filters.dimensions),
                or_(created_in_period, won_in_period, lost_in_period),
            )
            .group_by(Customer.province)
            .order_by(Customer.province.asc().nulls_last())
        ).all()

        metrics: list[ProvinceMetrics] = []
        for row in rows:
            won_kg = self._kg(row[5])
            lost_kg = self._kg(row[6])
            metrics.append(
                ProvinceMetrics(
                    province=row[0],
                    opportunities_created=row[1],
                    opportunities_won=row[2],
                    opportunities_lost=row[3],
                    conversion_rate=conversion_rate(row[2], row[2] + row[3]),
                    kg_quoted=self._kg(row[4]),
                    kg_won=won_kg,
                    kg_lost=lost_kg,
                )
            )
        return metrics

    def timeline(
        self,
        filters: MetricsFilters,
        *,
        granularity: TimelineGranularity,
    ) -> list[TimelineBucket]:
        period = filters.period
        self._validate_timeline_period(period, granularity)
        line_totals = self._line_totals(filters.dimensions)
        created_bucket = self._business_bucket(
            Opportunity.created_at,
            granularity,
        )
        closed_bucket = self._business_bucket(
            Opportunity.current_status_entered_at,
            granularity,
        )
        base_filters = self._opportunity_filters(filters.dimensions)
        created_statement = select(
            created_bucket,
            func.count(Opportunity.id),
        ).select_from(Opportunity)
        if filters.dimensions.province is not None:
            created_statement = created_statement.join(Customer)
        created_rows = self._session.execute(
            created_statement.where(
                *base_filters,
                self._in_period(Opportunity.created_at, period),
            ).group_by(created_bucket)
        ).all()
        closed_statement = (
            select(
                closed_bucket,
                func.count(Opportunity.id).filter(
                    Opportunity.status == OpportunityStatus.GANADA
                ),
                func.count(Opportunity.id).filter(
                    Opportunity.status == OpportunityStatus.PERDIDA
                ),
                func.sum(line_totals.c.total_kg).filter(
                    Opportunity.status == OpportunityStatus.GANADA
                ),
                func.sum(line_totals.c.total_kg).filter(
                    Opportunity.status == OpportunityStatus.PERDIDA
                ),
            )
            .select_from(Opportunity)
            .outerjoin(line_totals, line_totals.c.opportunity_id == Opportunity.id)
        )
        if filters.dimensions.province is not None:
            closed_statement = closed_statement.join(Customer)
        closed_rows = self._session.execute(
            closed_statement.where(
                *base_filters,
                Opportunity.status.in_(TERMINAL_OPPORTUNITY_STATUSES),
                self._in_period(Opportunity.current_status_entered_at, period),
            ).group_by(closed_bucket)
        ).all()

        created_by_bucket = {row[0]: row[1] for row in created_rows}
        closed_by_bucket = {row[0]: row[1:] for row in closed_rows}
        return [
            TimelineBucket(
                bucket=bucket,
                leads_created=created_by_bucket.get(bucket, 0),
                won=closed_by_bucket.get(bucket, (0, 0, None, None))[0],
                lost=closed_by_bucket.get(bucket, (0, 0, None, None))[1],
                kg_won=self._kg(closed_by_bucket.get(bucket, (0, 0, None, None))[2]),
                kg_lost=self._kg(closed_by_bucket.get(bucket, (0, 0, None, None))[3]),
            )
            for bucket in self._period_buckets(period, granularity)
        ]

    def timeline_day_opportunities(
        self,
        *,
        bucket: date,
        series: TimelineOpportunitySeries,
        dimensions: MetricsDimensions,
        page: int,
        page_size: int,
    ) -> tuple[list[Opportunity], int]:
        """Return the bounded Opportunities behind one exact timeline day bucket."""
        period = self._day_period(bucket)
        relevant_timestamp = (
            Opportunity.created_at
            if series is TimelineOpportunitySeries.CREATED
            else Opportunity.current_status_entered_at
        )
        filters = [
            *self._opportunity_filters(dimensions),
            self._in_period(relevant_timestamp, period),
        ]
        if series is TimelineOpportunitySeries.WON:
            filters.append(Opportunity.status == OpportunityStatus.GANADA)
        elif series is TimelineOpportunitySeries.LOST:
            filters.append(Opportunity.status == OpportunityStatus.PERDIDA)

        count_statement = select(func.count()).select_from(Opportunity)
        statement = select(Opportunity)
        if dimensions.province is not None:
            count_statement = count_statement.join(Customer)
            statement = statement.join(Customer)

        total = self._session.scalar(count_statement.where(*filters)) or 0
        opportunities = list(
            self._session.scalars(
                statement
                .where(*filters)
                .options(
                    joinedload(Opportunity.customer),
                    selectinload(Opportunity.opportunity_products).joinedload(
                        OpportunityProduct.product
                    ),
                )
                .order_by(relevant_timestamp.desc(), Opportunity.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return opportunities, total

    def pipeline(
        self,
        dimensions: MetricsDimensions,
    ) -> list[PipelineStatusMetrics]:
        statement = select(
            Opportunity.status,
            func.count(Opportunity.id),
        ).select_from(Opportunity)
        if dimensions.province is not None:
            statement = statement.join(Customer)
        rows = self._session.execute(
            statement.where(*self._opportunity_filters(dimensions)).group_by(
                Opportunity.status
            )
        ).all()
        counts = {row[0]: row[1] for row in rows}
        return [
            PipelineStatusMetrics(status=status, count=counts.get(status, 0))
            for status in OpportunityStatus
        ]

    def _opportunity_filters(
        self,
        dimensions: MetricsDimensions,
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = [Opportunity.deleted_at.is_(None)]
        if dimensions.source is not None:
            filters.append(Opportunity.source == dimensions.source)
        if dimensions.province is not None:
            filters.append(
                func.lower(func.btrim(Customer.province))
                == dimensions.province.strip().lower()
            )
        if dimensions.product_id is not None:
            filters.append(
                exists(
                    select(1).where(
                        OpportunityProduct.opportunity_id == Opportunity.id,
                        OpportunityProduct.product_id == dimensions.product_id,
                    )
                )
            )
        return filters

    def _line_filters(
        self,
        dimensions: MetricsDimensions,
    ) -> list[ColumnElement[bool]]:
        filters = self._opportunity_filters(
            MetricsDimensions(
                source=dimensions.source,
                province=dimensions.province,
            )
        )
        if dimensions.product_id is not None:
            filters.append(OpportunityProduct.product_id == dimensions.product_id)
        return filters

    @staticmethod
    def _line_totals(dimensions: MetricsDimensions) -> Subquery:
        statement = select(
            OpportunityProduct.opportunity_id.label("opportunity_id"),
            func.sum(OpportunityProduct.quantity_kg).label("total_kg"),
        )
        if dimensions.product_id is not None:
            statement = statement.where(
                OpportunityProduct.product_id == dimensions.product_id
            )
        return statement.group_by(OpportunityProduct.opportunity_id).subquery()

    @staticmethod
    def _in_period(
        timestamp: SQLColumnExpression[datetime],
        period: MetricsPeriod,
    ) -> ColumnElement[bool]:
        return and_(timestamp >= period.start, timestamp < period.end)

    @staticmethod
    def _day_period(bucket: date) -> MetricsPeriod:
        local_start = datetime.combine(bucket, time.min, tzinfo=BUSINESS_TIMEZONE)
        local_end = local_start + timedelta(days=1)
        return MetricsPeriod(
            start=local_start.astimezone(UTC),
            end=local_end.astimezone(UTC),
        )

    @staticmethod
    def _business_bucket(
        timestamp: SQLColumnExpression[datetime],
        granularity: TimelineGranularity,
    ) -> ColumnElement[date]:
        return cast(
            func.date_trunc(
                granularity.value,
                func.timezone(BUSINESS_TIMEZONE_NAME, timestamp),
            ),
            Date,
        )

    @staticmethod
    def _period_buckets(
        period: MetricsPeriod,
        granularity: TimelineGranularity,
    ) -> list[date]:
        local_start = period.start.astimezone(BUSINESS_TIMEZONE)
        local_last = (period.end - timedelta(microseconds=1)).astimezone(
            BUSINESS_TIMEZONE
        )
        current = local_start.date()
        last = local_last.date()
        if granularity is TimelineGranularity.MONTH:
            current = current.replace(day=1)
            last = last.replace(day=1)

        buckets: list[date] = []
        while current <= last:
            buckets.append(current)
            current = (
                current + timedelta(days=1)
                if granularity is TimelineGranularity.DAY
                else MetricsService._next_month(current)
            )
        return buckets

    @staticmethod
    def _validate_timeline_period(
        period: MetricsPeriod,
        granularity: TimelineGranularity,
    ) -> None:
        local_start = period.start.astimezone(BUSINESS_TIMEZONE).date()
        local_last = (
            (period.end - timedelta(microseconds=1))
            .astimezone(BUSINESS_TIMEZONE)
            .date()
        )
        if granularity is TimelineGranularity.DAY:
            requested = (local_last - local_start).days + 1
            maximum = MAX_DAY_TIMELINE_BUCKETS
        else:
            requested = (
                (local_last.year - local_start.year) * 12
                + local_last.month
                - local_start.month
                + 1
            )
            maximum = MAX_MONTH_TIMELINE_BUCKETS
        if requested > maximum:
            raise MetricsTimelinePeriodTooLargeError(
                granularity=granularity.value,
                requested_bucket_count=requested,
                maximum_bucket_count=maximum,
            )

    @staticmethod
    def _next_month(value: date) -> date:
        if value.month == 12:
            return date(value.year + 1, 1, 1)
        return date(value.year, value.month + 1, 1)

    @staticmethod
    def _kg(value: Decimal | None) -> Decimal:
        return value if value is not None else ZERO_KG
