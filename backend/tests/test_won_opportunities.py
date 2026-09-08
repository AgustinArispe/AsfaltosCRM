from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    Product,
    User,
    UserRole,
)
from app.services.opportunity_query_service import OpportunityQueryService
from app.services.won_opportunity_service import WonFilters, WonOpportunityQueryService

AS_OF = datetime(2026, 9, 7, 15, tzinfo=UTC)


def won(
    db_session: Session, *, age: timedelta, quantity: str = "1000.000"
) -> Opportunity:
    customer = Customer(name=f"Cliente {age.total_seconds()}", province="Buenos Aires")
    product = Product(name=f"Producto {age.total_seconds()} {quantity}")
    opportunity = Opportunity(
        customer=customer,
        source=LeadSource.WEB,
        status=OpportunityStatus.GANADA,
        current_status_entered_at=AS_OF - age,
        created_at=AS_OF - age - timedelta(days=1),
    )
    opportunity.opportunity_products.append(
        OpportunityProduct(product=product, quantity_kg=Decimal(quantity))
    )
    db_session.add(opportunity)
    db_session.commit()
    return opportunity


def test_active_board_uses_exact_utc_interval_and_preserves_generic_query(
    db_session: Session,
) -> None:
    included = won(db_session, age=timedelta(days=29, hours=23, minutes=59))
    exact = won(db_session, age=timedelta(days=30))
    older = won(db_session, age=timedelta(days=31))
    future = won(db_session, age=timedelta(seconds=-1))
    service = OpportunityQueryService(db_session)

    active, total = service.list_opportunities(
        page=1,
        page_size=100,
        status=OpportunityStatus.GANADA,
        customer_id=None,
        assigned_user_id=None,
        source=None,
        active_board=True,
        as_of=AS_OF,
    )
    generic, generic_total = service.list_opportunities(
        page=1,
        page_size=100,
        status=OpportunityStatus.GANADA,
        customer_id=None,
        assigned_user_id=None,
        source=None,
    )

    assert [item.id for item in active] == [included.id]
    assert total == 1
    assert {item.id for item in generic} == {included.id, exact.id, older.id, future.id}
    assert generic_total == 4


def test_won_history_cursor_statistics_and_bounded_hydration(
    db_session: Session,
) -> None:
    first = won(db_session, age=timedelta(days=40), quantity="100.125")
    second = won(db_session, age=timedelta(days=40), quantity="200.250")
    queries = 0

    def count_queries(
        _connection: Connection,
        _cursor: object,
        _statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        nonlocal queries
        queries += 1

    event.listen(db_session.bind, "before_cursor_execute", count_queries)
    try:
        page = WonOpportunityQueryService(db_session).list(
            WonFilters(), limit=1, cursor=None
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", count_queries)
    assert len(page.items) == 1
    assert page.next_cursor is not None
    following = WonOpportunityQueryService(db_session).list(
        WonFilters(), limit=1, cursor=page.next_cursor
    )
    assert {page.items[0].opportunity.id, following.items[0].opportunity.id} == {
        first.id,
        second.id,
    }
    assert queries <= 4
    statistics = WonOpportunityQueryService(db_session).statistics(WonFilters())
    assert statistics.won_count == 2
    assert statistics.won_quantity_kg == Decimal("300.375")


def test_won_api_validation_and_history_visibility(
    api_client: TestClient, db_session: Session
) -> None:
    opportunity = won(db_session, age=timedelta(days=45))
    assert (
        api_client.get("/api/opportunities", params={"active_board": True}).status_code
        == 422
    )
    board = api_client.get(
        "/api/opportunities", params={"status": "GANADA", "active_board": True}
    )
    history = api_client.get("/api/won-opportunities")
    assert board.status_code == history.status_code == 200
    assert opportunity.id not in {item["id"] for item in board.json()["items"]}
    item = next(
        item
        for item in history.json()["items"]
        if item["opportunity"]["id"] == opportunity.id
    )
    assert item["won_at"] == item["opportunity"]["current_status_entered_at"]
    assert (
        api_client.get(
            "/api/won-opportunities", params={"cursor": "not-valid"}
        ).status_code
        == 409
    )
    assert (
        api_client.get(
            "/api/won-opportunities", params={"won_from": "2026-09-01T00:00:00"}
        ).status_code
        == 422
    )


def test_active_board_does_not_change_non_won_stages(db_session: Session) -> None:
    customer = Customer(name="Cliente etapas")
    db_session.add(customer)
    db_session.flush()
    opportunities = [
        Opportunity(
            customer_id=customer.id,
            source=LeadSource.WEB,
            status=stage,
            current_status_entered_at=AS_OF - timedelta(days=90),
            created_at=AS_OF - timedelta(days=100),
        )
        for stage in (
            OpportunityStatus.NUEVA,
            OpportunityStatus.COTIZADA,
            OpportunityStatus.NEGOCIACION,
        )
    ]
    db_session.add_all(opportunities)
    db_session.commit()
    service = OpportunityQueryService(db_session)

    for opportunity in opportunities:
        rows, total = service.list_opportunities(
            page=1,
            page_size=100,
            status=opportunity.status,
            customer_id=None,
            assigned_user_id=None,
            source=None,
            active_board=True,
            as_of=AS_OF,
        )
        assert [row.id for row in rows] == [opportunity.id]
        assert total == 1


def test_won_filters_keep_complete_quote_and_historical_options(
    api_client: TestClient, db_session: Session
) -> None:
    seller = User(
        full_name="Vendedora histórica",
        email="historica-won@faa.test",
        password_hash="unused",
        role=UserRole.VENDEDOR,
        is_active=False,
    )
    matching = won(db_session, age=timedelta(days=7), quantity="100.000")
    matching.customer.name = "María Austral"
    matching.customer.company = "Vial Austral SA"
    matching.customer.province = "Córdoba"
    matching.source = LeadSource.WHATSAPP
    matching.assigned_user = seller
    first_product = matching.opportunity_products[0].product
    first_product.is_active = False
    extra_product = Product(name="Producto adicional")
    matching.opportunity_products.append(
        OpportunityProduct(product=extra_product, quantity_kg=Decimal("250.000"))
    )
    unassigned = won(db_session, age=timedelta(days=8), quantity="50.000")
    db_session.commit()

    common: dict[str, str | int] = {
        "search": str(matching.id),
        "product_id": first_product.id,
        "source": "WHATSAPP",
        "province": " córdoba ",
        "assigned_user_id": seller.id,
        "won_from": "2026-08-01T00:00:00-03:00",
        "won_to": "2026-10-01T00:00:00-03:00",
    }
    listing = api_client.get("/api/won-opportunities", params=common)
    statistics = api_client.get("/api/won-opportunities/statistics", params=common)
    assert listing.status_code == statistics.status_code == 200
    assert [item["opportunity"]["id"] for item in listing.json()["items"]] == [
        matching.id
    ]
    assert listing.json()["items"][0]["won_total_kg"] == "350.000"
    assert statistics.json() == {"won_count": 1, "won_quantity_kg": "350.000"}

    assert (
        api_client.get(
            "/api/won-opportunities", params={"search": "Vial Austral"}
        ).json()["items"][0]["opportunity"]["id"]
        == matching.id
    )
    assert (
        api_client.get("/api/won-opportunities", params={"unassigned": True}).json()[
            "items"
        ][0]["opportunity"]["id"]
        == unassigned.id
    )
    assert (
        api_client.get(
            "/api/won-opportunities",
            params={"assigned_user_id": seller.id, "unassigned": True},
        ).status_code
        == 422
    )

    options = api_client.get("/api/won-opportunities/filter-options").json()
    assert {item["id"] for item in options["products"]} >= {
        first_product.id,
        extra_product.id,
    }
    assert (
        next(item for item in options["products"] if item["id"] == first_product.id)[
            "is_active"
        ]
        is False
    )
    assert {item["id"] for item in options["responsible_users"]} == {seller.id}
    assert options["responsible_users"][0]["is_active"] is False
    assert "Córdoba" in options["provinces"]


def test_won_date_filter_honors_buenos_aires_boundary(
    api_client: TestClient, db_session: Session
) -> None:
    before_midnight = won(db_session, age=timedelta(days=6, hours=12, minutes=1))
    at_midnight = won(db_session, age=timedelta(days=6, hours=12))
    response = api_client.get(
        "/api/won-opportunities",
        params={
            "won_from": "2026-09-01T00:00:00-03:00",
            "won_to": "2026-09-02T00:00:00-03:00",
        },
    )
    ids = {item["opportunity"]["id"] for item in response.json()["items"]}
    assert at_midnight.id in ids
    assert before_midnight.id not in ids


def test_both_roles_can_read_won_history(
    api_client: TestClient, db_session: Session
) -> None:
    opportunity = won(db_session, age=timedelta(days=1))
    seller = User(
        full_name="Vendedor lector",
        email="lector-won@faa.test",
        password_hash="unused",
        role=UserRole.VENDEDOR,
    )
    db_session.add(seller)
    db_session.commit()
    original_authorization = api_client.headers["Authorization"]
    try:
        api_client.headers["Authorization"] = f"Bearer {create_access_token(seller.id)}"
        response = api_client.get("/api/won-opportunities")
    finally:
        api_client.headers["Authorization"] = original_authorization
    assert response.status_code == 200
    assert opportunity.id in {
        item["opportunity"]["id"] for item in response.json()["items"]
    }


def test_won_statistics_zero(db_session: Session) -> None:
    statistics = WonOpportunityQueryService(db_session).statistics(WonFilters())
    assert statistics.won_count == 0
    assert statistics.won_quantity_kg == Decimal(0)
