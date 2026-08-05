from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    LossReason,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    Product,
)
from app.services.metrics_service import (
    MetricsDimensions,
    MetricsFilters,
    MetricsPeriod,
    MetricsService,
    TimelineGranularity,
    conversion_rate,
)

PERIOD_START = datetime(2040, 1, 1, tzinfo=UTC)
PERIOD_END = datetime(2040, 2, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class MetricLine:
    product: Product
    quantity_kg: Decimal


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def make_customer(
    db_session: Session,
    *,
    province: str | None = "Buenos Aires",
    deleted: bool = False,
) -> Customer:
    customer = Customer(
        name=f"Cliente métricas {uuid4().hex}",
        province=province,
        deleted_at=PERIOD_END if deleted else None,
    )
    persist(db_session, customer)
    return customer


def make_product(
    db_session: Session,
    *,
    name: str = "Producto métricas",
    active: bool = True,
) -> Product:
    product = Product(name=f"{name} {uuid4().hex}", is_active=active)
    persist(db_session, product)
    return product


def make_opportunity(
    db_session: Session,
    customer: Customer,
    *,
    status: OpportunityStatus,
    created_at: datetime,
    entered_at: datetime | None = None,
    source: LeadSource = LeadSource.WEB,
    lines: Sequence[MetricLine] = (),
    deleted: bool = False,
) -> Opportunity:
    status_entered_at = entered_at or created_at
    opportunity = Opportunity(
        customer=customer,
        source=source,
        status=status,
        loss_reason=(LossReason.OTRO if status is OpportunityStatus.PERDIDA else None),
        created_at=created_at,
        updated_at=status_entered_at,
        current_status_entered_at=status_entered_at,
        deleted_at=status_entered_at + timedelta(days=1) if deleted else None,
    )
    opportunity.opportunity_products.extend(
        OpportunityProduct(product=line.product, quantity_kg=line.quantity_kg)
        for line in lines
    )
    persist(db_session, opportunity)
    return opportunity


def filters(
    *,
    start: datetime = PERIOD_START,
    end: datetime = PERIOD_END,
    source: LeadSource | None = None,
    product_id: int | None = None,
    province: str | None = None,
) -> MetricsFilters:
    return MetricsFilters(
        period=MetricsPeriod(start=start, end=end),
        dimensions=MetricsDimensions(
            source=source,
            product_id=product_id,
            province=province,
        ),
    )


def test_conversion_rate_is_precise_and_null_for_zero_denominator() -> None:
    assert conversion_rate(7, 10) == Decimal("0.7000")
    assert conversion_rate(Decimal("90"), Decimal("100")) == Decimal("0.9000")
    assert conversion_rate(0, 0) is None


def test_metrics_period_requires_aware_ordered_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        MetricsPeriod(
            start=datetime(2040, 1, 1),
            end=datetime(2040, 1, 2),
        )
    with pytest.raises(ValueError, match="start must be before end"):
        MetricsPeriod(start=PERIOD_END, end=PERIOD_START)


def test_overview_without_data_returns_zeroes_and_null_ratios(
    db_session: Session,
) -> None:
    overview = MetricsService(db_session).overview(filters())

    assert overview.opportunities.created == 0
    assert overview.opportunities.won == 0
    assert overview.opportunities.lost == 0
    assert overview.opportunities.open == 0
    assert overview.opportunities.conversion_rate is None
    assert overview.volume_kg.quoted == Decimal("0.000")
    assert overview.volume_kg.won == Decimal("0.000")
    assert overview.volume_kg.lost == Decimal("0.000")
    assert overview.volume_kg.open == Decimal("0.000")
    assert overview.volume_kg.conversion_rate is None


def test_overview_calculates_closed_conversion_and_independent_volume(
    db_session: Session,
) -> None:
    customer = make_customer(db_session)
    product_a = make_product(db_session, name="A")
    product_b = make_product(db_session, name="B")
    created_at = PERIOD_START + timedelta(days=2)
    closed_at = PERIOD_START + timedelta(days=5)

    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(
            MetricLine(product_a, Decimal("20000")),
            MetricLine(product_b, Decimal("10000")),
        ),
    )
    for _ in range(6):
        make_opportunity(
            db_session,
            customer,
            status=OpportunityStatus.GANADA,
            created_at=created_at,
            entered_at=closed_at,
            lines=(MetricLine(product_a, Decimal("10000")),),
        )
    for _ in range(2):
        make_opportunity(
            db_session,
            customer,
            status=OpportunityStatus.PERDIDA,
            created_at=created_at,
            entered_at=closed_at,
            lines=(MetricLine(product_a, Decimal("5000")),),
        )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.PERDIDA,
        created_at=created_at,
        entered_at=closed_at,
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.COTIZADA,
        created_at=created_at,
        lines=(MetricLine(product_a, Decimal("10000")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.NEGOCIACION,
        created_at=created_at,
        lines=(MetricLine(product_a, Decimal("10000")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.NUEVA,
        created_at=created_at,
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(MetricLine(product_a, Decimal("999999")),),
        deleted=True,
    )

    overview = MetricsService(db_session).overview(filters())

    assert overview.opportunities.created == 13
    assert overview.opportunities.won == 7
    assert overview.opportunities.lost == 3
    assert overview.opportunities.open == 3
    assert overview.opportunities.conversion_rate == Decimal("0.7000")
    assert overview.volume_kg.quoted == Decimal("120000.000")
    assert overview.volume_kg.won == Decimal("90000.000")
    assert overview.volume_kg.lost == Decimal("10000.000")
    assert overview.volume_kg.open == Decimal("20000.000")
    assert overview.volume_kg.conversion_rate == Decimal("0.9000")


def test_overview_uses_creation_for_leads_and_terminal_entry_for_closures(
    db_session: Session,
) -> None:
    customer = make_customer(db_session)
    product = make_product(db_session)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=PERIOD_START - timedelta(days=30),
        entered_at=PERIOD_START + timedelta(days=1),
        lines=(MetricLine(product, Decimal("100")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=PERIOD_START + timedelta(days=1),
        entered_at=PERIOD_END + timedelta(days=1),
        lines=(MetricLine(product, Decimal("200")),),
    )

    overview = MetricsService(db_session).overview(filters())

    assert overview.opportunities.created == 1
    assert overview.opportunities.won == 1
    assert overview.volume_kg.quoted == Decimal("200.000")
    assert overview.volume_kg.won == Decimal("100.000")


def test_overview_dimensions_filter_source_product_and_normalized_province(
    db_session: Session,
) -> None:
    customer = make_customer(db_session, province=" Buenos Aires ")
    product = make_product(db_session)
    other_product = make_product(db_session)
    created_at = PERIOD_START + timedelta(days=1)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.COTIZADA,
        created_at=created_at,
        source=LeadSource.WHATSAPP,
        lines=(MetricLine(product, Decimal("75")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.COTIZADA,
        created_at=created_at,
        source=LeadSource.WEB,
        lines=(MetricLine(other_product, Decimal("500")),),
    )

    overview = MetricsService(db_session).overview(
        filters(
            source=LeadSource.WHATSAPP,
            product_id=product.id,
            province="buenos aires",
        )
    )

    assert overview.opportunities.created == 1
    assert overview.volume_kg.quoted == Decimal("75.000")


def test_product_metrics_group_by_id_include_inactive_and_order_by_quoted_kg(
    db_session: Session,
) -> None:
    customer = make_customer(db_session)
    product_a = make_product(db_session, name="A")
    product_b = make_product(db_session, name="B", active=False)
    created_at = PERIOD_START + timedelta(days=1)
    closed_at = PERIOD_START + timedelta(days=2)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(
            MetricLine(product_a, Decimal("100")),
            MetricLine(product_b, Decimal("300")),
        ),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.PERDIDA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(MetricLine(product_a, Decimal("50")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.COTIZADA,
        created_at=created_at,
        lines=(MetricLine(product_a, Decimal("25")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.PERDIDA,
        created_at=created_at,
        entered_at=closed_at,
    )

    metrics = MetricsService(db_session).products(filters())

    assert [item.product_id for item in metrics] == [product_b.id, product_a.id]
    by_id = {item.product_id: item for item in metrics}
    a = by_id[product_a.id]
    assert a.opportunities_quoted == 3
    assert a.kg_quoted == Decimal("175.000")
    assert a.opportunities_won == 1
    assert a.kg_won == Decimal("100.000")
    assert a.opportunities_lost == 1
    assert a.kg_lost == Decimal("50.000")
    assert a.conversion_rate_opportunities == Decimal("0.5000")
    assert a.conversion_rate_kg == Decimal("0.6667")
    assert by_id[product_b.id].opportunities_won == 1


def test_product_metrics_can_filter_one_product(db_session: Session) -> None:
    customer = make_customer(db_session)
    product = make_product(db_session)
    other = make_product(db_session)
    created_at = PERIOD_START + timedelta(days=1)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.COTIZADA,
        created_at=created_at,
        lines=(
            MetricLine(product, Decimal("10")),
            MetricLine(other, Decimal("20")),
        ),
    )

    metrics = MetricsService(db_session).products(filters(product_id=product.id))

    assert len(metrics) == 1
    assert metrics[0].product_id == product.id
    assert metrics[0].kg_quoted == Decimal("10.000")


def test_source_metrics_support_each_enum_and_closed_ratios(
    db_session: Session,
) -> None:
    customer = make_customer(db_session)
    created_at = PERIOD_START + timedelta(days=1)
    closed_at = PERIOD_START + timedelta(days=2)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=created_at,
        entered_at=closed_at,
        source=LeadSource.WEB,
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.PERDIDA,
        created_at=created_at,
        entered_at=closed_at,
        source=LeadSource.WEB,
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.NUEVA,
        created_at=created_at,
        source=LeadSource.WHATSAPP,
    )

    metrics = MetricsService(db_session).sources(filters())
    by_source = {item.source: item for item in metrics}

    assert by_source[LeadSource.WEB].created == 2
    assert by_source[LeadSource.WEB].won == 1
    assert by_source[LeadSource.WEB].lost == 1
    assert by_source[LeadSource.WEB].conversion_rate == Decimal("0.5000")
    assert by_source[LeadSource.WHATSAPP].created == 1
    assert by_source[LeadSource.WHATSAPP].conversion_rate is None


def test_province_metrics_keep_null_and_soft_deleted_customer_history(
    db_session: Session,
) -> None:
    product = make_product(db_session)
    buenos_aires = make_customer(db_session, province="Buenos Aires")
    no_province = make_customer(db_session, province=None)
    archived = make_customer(db_session, province="Mendoza", deleted=True)
    created_at = PERIOD_START + timedelta(days=1)
    closed_at = PERIOD_START + timedelta(days=2)
    make_opportunity(
        db_session,
        buenos_aires,
        status=OpportunityStatus.GANADA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(MetricLine(product, Decimal("100")),),
    )
    make_opportunity(
        db_session,
        no_province,
        status=OpportunityStatus.PERDIDA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(MetricLine(product, Decimal("50")),),
    )
    make_opportunity(
        db_session,
        archived,
        status=OpportunityStatus.GANADA,
        created_at=created_at,
        entered_at=closed_at,
        lines=(MetricLine(product, Decimal("25")),),
    )

    metrics = MetricsService(db_session).provinces(filters())
    by_province = {item.province: item for item in metrics}

    assert by_province["Buenos Aires"].kg_won == Decimal("100.000")
    assert by_province[None].opportunities_lost == 1
    assert by_province[None].kg_lost == Decimal("50.000")
    assert by_province["Mendoza"].opportunities_won == 1
    assert by_province["Mendoza"].kg_won == Decimal("25.000")


def test_timeline_uses_buenos_aires_calendar_and_fills_empty_days(
    db_session: Session,
) -> None:
    start = datetime(2040, 1, 1, 3, tzinfo=UTC)
    end = datetime(2040, 1, 4, 3, tzinfo=UTC)
    customer = make_customer(db_session)
    product = make_product(db_session)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.GANADA,
        created_at=start - timedelta(days=5),
        entered_at=datetime(2040, 1, 2, 2, tzinfo=UTC),
        lines=(MetricLine(product, Decimal("125")),),
    )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.NUEVA,
        created_at=datetime(2040, 1, 3, 5, tzinfo=UTC),
    )

    buckets = MetricsService(db_session).timeline(
        filters(start=start, end=end),
        granularity=TimelineGranularity.DAY,
    )

    assert [bucket.bucket.isoformat() for bucket in buckets] == [
        "2040-01-01",
        "2040-01-02",
        "2040-01-03",
    ]
    assert buckets[0].won == 1
    assert buckets[0].kg_won == Decimal("125.000")
    assert buckets[1].leads_created == 0
    assert buckets[2].leads_created == 1


def test_timeline_month_buckets_include_empty_periods(db_session: Session) -> None:
    start = datetime(2040, 1, 1, 3, tzinfo=UTC)
    end = datetime(2040, 4, 1, 3, tzinfo=UTC)
    customer = make_customer(db_session)
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.PERDIDA,
        created_at=datetime(2040, 2, 5, 12, tzinfo=UTC),
        entered_at=datetime(2040, 2, 8, 12, tzinfo=UTC),
    )

    buckets = MetricsService(db_session).timeline(
        filters(start=start, end=end),
        granularity=TimelineGranularity.MONTH,
    )

    assert [bucket.bucket.isoformat() for bucket in buckets] == [
        "2040-01-01",
        "2040-02-01",
        "2040-03-01",
    ]
    assert buckets[0].leads_created == 0
    assert buckets[1].leads_created == 1
    assert buckets[1].lost == 1
    assert buckets[1].kg_lost == Decimal("0.000")
    assert buckets[2].lost == 0


def test_pipeline_is_current_snapshot_with_all_statuses_and_excludes_deleted(
    db_session: Session,
) -> None:
    province = f"Pipeline {uuid4().hex}"
    customer = make_customer(db_session, province=province)
    for status in OpportunityStatus:
        make_opportunity(
            db_session,
            customer,
            status=status,
            created_at=PERIOD_START,
        )
    make_opportunity(
        db_session,
        customer,
        status=OpportunityStatus.NUEVA,
        created_at=PERIOD_START,
        deleted=True,
    )

    metrics = MetricsService(db_session).pipeline(MetricsDimensions(province=province))

    assert [item.status for item in metrics] == list(OpportunityStatus)
    assert all(item.count == 1 for item in metrics)
