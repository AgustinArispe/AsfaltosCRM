from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    Product,
)
from app.schemas.metrics import (
    MetricsOverviewResponse,
    PipelineMetricsResponse,
    ProductMetricsResponse,
    ProvinceMetricsResponse,
    SourceMetricsResponse,
    TimelineDayOpportunitiesResponse,
    TimelineMetricsResponse,
)

FROM = datetime(2050, 1, 1, 3, tzinfo=UTC)
TO = datetime(2050, 2, 1, 3, tzinfo=UTC)


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def period_params() -> dict[str, str]:
    return {"from": FROM.isoformat(), "to": TO.isoformat()}


def seed_metrics_data(db_session: Session) -> tuple[Customer, Product, Opportunity]:
    unique = uuid4().hex
    customer = Customer(
        name=f"Cliente API métricas {unique}",
        province=f"Provincia API {unique}",
    )
    product = Product(name=f"Producto API métricas {unique}", is_active=False)
    won = Opportunity(
        customer=customer,
        source=LeadSource.WEB,
        status=OpportunityStatus.GANADA,
        created_at=FROM + timedelta(days=1),
        updated_at=FROM + timedelta(days=3),
        current_status_entered_at=FROM + timedelta(days=3),
    )
    won.opportunity_products.append(
        OpportunityProduct(product=product, quantity_kg=Decimal("2500"))
    )
    persist(db_session, won)
    return customer, product, won


@pytest.mark.parametrize(
    "path",
    [
        "/api/metrics/overview",
        "/api/metrics/products",
        "/api/metrics/sources",
        "/api/metrics/provinces",
        "/api/metrics/timeline",
    ],
)
def test_period_metrics_require_authentication(
    api_client: TestClient,
    path: str,
) -> None:
    del api_client.headers["Authorization"]

    response = api_client.get(path, params=period_params())

    assert response.status_code == 401


def test_pipeline_metrics_require_authentication(api_client: TestClient) -> None:
    del api_client.headers["Authorization"]
    assert api_client.get("/api/metrics/pipeline").status_code == 401


def test_timeline_day_opportunities_requires_authentication(
    api_client: TestClient,
) -> None:
    del api_client.headers["Authorization"]
    response = api_client.get(
        "/api/metrics/timeline/day-opportunities",
        params={"bucket": "2050-01-04", "series": "won"},
    )
    assert response.status_code == 401


def test_all_metric_endpoints_return_typed_contracts(
    api_client: TestClient,
    db_session: Session,
) -> None:
    customer, product, won = seed_metrics_data(db_session)
    params = period_params()

    overview_response = api_client.get("/api/metrics/overview", params=params)
    products_response = api_client.get("/api/metrics/products", params=params)
    sources_response = api_client.get("/api/metrics/sources", params=params)
    provinces_response = api_client.get("/api/metrics/provinces", params=params)
    timeline_response = api_client.get(
        "/api/metrics/timeline",
        params={**params, "granularity": "day"},
    )
    pipeline_response = api_client.get(
        "/api/metrics/pipeline",
        params={"province": customer.province},
    )

    assert overview_response.status_code == 200
    assert products_response.status_code == 200
    assert sources_response.status_code == 200
    assert provinces_response.status_code == 200
    assert timeline_response.status_code == 200
    assert pipeline_response.status_code == 200

    overview = MetricsOverviewResponse.model_validate(overview_response.json())
    products = ProductMetricsResponse.model_validate(products_response.json())
    sources = SourceMetricsResponse.model_validate(sources_response.json())
    provinces = ProvinceMetricsResponse.model_validate(provinces_response.json())
    timeline = TimelineMetricsResponse.model_validate(timeline_response.json())
    pipeline = PipelineMetricsResponse.model_validate(pipeline_response.json())

    assert "from" in overview_response.json()["period"]
    assert "start" not in overview_response.json()["period"]
    assert overview.opportunities.created == 1
    assert overview.opportunities.won == 1
    assert overview.opportunities.conversion_rate == Decimal("1.0000")
    assert overview.volume_kg.won == Decimal("2500.000")
    assert products.items[0].product_id == product.id
    assert products.items[0].kg_quoted == Decimal("2500.000")
    assert sources.items[0].source is LeadSource.WEB
    assert provinces.items[0].province == customer.province
    assert len(timeline.items) == 31
    assert sum(item.won for item in timeline.items) == 1
    pipeline_by_status = {item.status: item.count for item in pipeline.items}
    assert pipeline_by_status[OpportunityStatus.GANADA] == 1
    assert pipeline.snapshot_at.tzinfo is not None
    assert won.id > 0


def test_metric_filters_are_applied_through_api(
    api_client: TestClient,
    db_session: Session,
) -> None:
    customer, product, _ = seed_metrics_data(db_session)
    assert customer.province is not None
    response = api_client.get(
        "/api/metrics/overview",
        params={
            **period_params(),
            "source": "WEB",
            "product_id": product.id,
            "province": f"  {customer.province.lower()}  ",
        },
    )
    excluded = api_client.get(
        "/api/metrics/overview",
        params={**period_params(), "source": "WHATSAPP"},
    )

    assert response.status_code == 200
    assert response.json()["opportunities"]["created"] == 1
    assert excluded.status_code == 200
    assert excluded.json()["opportunities"]["created"] == 0


def test_timeline_day_opportunities_returns_narrow_typed_projection(
    api_client: TestClient,
    db_session: Session,
) -> None:
    customer, product, won = seed_metrics_data(db_session)
    assert customer.province is not None

    response = api_client.get(
        "/api/metrics/timeline/day-opportunities",
        params={
            "bucket": date(2050, 1, 4).isoformat(),
            "series": "won",
            "source": "WEB",
            "product_id": product.id,
            "province": customer.province,
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    detail = TimelineDayOpportunitiesResponse.model_validate(payload)
    assert detail.total == 1
    assert detail.timezone == "America/Argentina/Buenos_Aires"
    assert detail.items[0].opportunity_id == won.id
    assert detail.items[0].customer_name == customer.name
    assert detail.items[0].current_status is OpportunityStatus.GANADA
    assert detail.items[0].products[0].quantity_kg == Decimal("2500.000")
    assert set(payload["items"][0]) == {
        "opportunity_id",
        "customer_name",
        "customer_company",
        "current_status",
        "source",
        "products",
    }


@pytest.mark.parametrize(
    "params",
    [
        {"bucket": "2050-01-04", "series": "closed"},
        {"bucket": "2050-01-04", "series": "won", "page": 0},
        {"bucket": "2050-01-04", "series": "won", "page_size": 101},
        {"bucket": "not-a-date", "series": "won"},
        {"bucket": "2050-01-04", "series": "won", "unexpected": "value"},
    ],
)
def test_timeline_day_opportunities_validates_query(
    api_client: TestClient,
    params: dict[str, object],
) -> None:
    response = api_client.get(
        "/api/metrics/timeline/day-opportunities",
        params=params,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2050-01-01T00:00:00", "to": TO.isoformat()},
        {"from": TO.isoformat(), "to": FROM.isoformat()},
        {**period_params(), "product_id": "0"},
        {**period_params(), "source": "META"},
        {**period_params(), "unexpected": "value"},
    ],
)
def test_period_metric_query_validation(
    api_client: TestClient,
    params: dict[str, str],
) -> None:
    assert api_client.get("/api/metrics/overview", params=params).status_code == 422


def test_timeline_rejects_unsupported_granularity(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/metrics/timeline",
        params={**period_params(), "granularity": "week"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("granularity", "start", "end", "requested", "maximum"),
    [
        (
            "day",
            datetime(2040, 1, 1, 3, tzinfo=UTC),
            datetime(2041, 1, 2, 3, tzinfo=UTC),
            367,
            366,
        ),
        (
            "month",
            datetime(2000, 1, 1, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires")),
            datetime(2100, 2, 1, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires")),
            1_201,
            1_200,
        ),
    ],
)
def test_timeline_oversized_period_has_typed_422(
    api_client: TestClient,
    granularity: str,
    start: datetime,
    end: datetime,
    requested: int,
    maximum: int,
) -> None:
    response = api_client.get(
        "/api/metrics/timeline",
        params={
            "from": start.isoformat(),
            "to": end.isoformat(),
            "granularity": granularity,
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "METRICS_TIMELINE_PERIOD_TOO_LARGE",
            "granularity": granularity,
            "requested_bucket_count": requested,
            "maximum_bucket_count": maximum,
        }
    }


def test_pipeline_rejects_period_and_invalid_product_filter(
    api_client: TestClient,
) -> None:
    with_period = api_client.get(
        "/api/metrics/pipeline",
        params=period_params(),
    )
    invalid_product = api_client.get(
        "/api/metrics/pipeline",
        params={"product_id": 0},
    )

    assert with_period.status_code == 422
    assert invalid_product.status_code == 422
