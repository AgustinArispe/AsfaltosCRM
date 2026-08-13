from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import (
    CUSTOMER_IMPORT_REQUEST_MAX_BYTES,
    META_WEBHOOK_BODY_MAX_BYTES,
    WEB_INTAKE_BODY_MAX_BYTES,
    WHATSAPP_MEDIA_REQUEST_MAX_BYTES,
)
from app.core.security import create_access_token, hash_password
from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
    OpportunityStatusHistory,
    Product,
    User,
    UserRole,
)
from app.services.customer_service import CustomerService
from app.services.errors import DuplicateEntityError, StaleWriteConflictError
from app.services.opportunity_query_service import OpportunityQueryService
from app.services.product_service import ProductService
from app.services.user_service import UserService


def unique_label(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def test_request_contracts_validate_emails_and_reject_internal_fields(
    api_client: TestClient,
) -> None:
    customer = api_client.post(
        "/api/customers",
        json={
            "name": unique_label("Cliente contrato"),
            "email": "ventas+obra@faa.com.ar",
            "phone": "+54 (11) 4444-5555 interno 23",
        },
    )
    assert customer.status_code == 201
    assert customer.json()["phone"] == "+54 (11) 4444-5555 interno 23"

    assert (
        api_client.post(
            "/api/customers",
            json={"name": "Email inválido", "email": "not-an-email"},
        ).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/users",
            json={
                "full_name": "Email inválido",
                "email": "missing-at-sign",
                "password": "valid-test-password",
                "role": "VENDEDOR",
            },
        ).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/products",
            json={"name": "Producto interno", "id": 999},
        ).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/users",
            json={
                "full_name": "Hash prohibido",
                "email": "hash-prohibido@faa.test",
                "password": "valid-test-password",
                "password_hash": "must-not-be-accepted",
                "role": "VENDEDOR",
            },
        ).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/opportunities",
            json={
                "customer_id": customer.json()["id"],
                "source": "WEB",
                "status": "GANADA",
            },
        ).status_code
        == 422
    )


def test_untrusted_host_is_rejected(api_client: TestClient) -> None:
    response = api_client.get(
        "/health",
        headers={"Host": "untrusted.example"},
    )
    assert response.status_code == 400
    assert response.text == "Invalid host header"


@pytest.mark.parametrize(
    ("path", "maximum"),
    [
        ("/api/intake/web", WEB_INTAKE_BODY_MAX_BYTES),
        ("/api/whatsapp/provider/webhook", META_WEBHOOK_BODY_MAX_BYTES),
        ("/api/whatsapp/media", WHATSAPP_MEDIA_REQUEST_MAX_BYTES),
        ("/api/customer-imports/dry-run", CUSTOMER_IMPORT_REQUEST_MAX_BYTES),
    ],
)
def test_protected_request_bodies_are_rejected_before_application_parsing(
    api_client: TestClient,
    path: str,
    maximum: int,
) -> None:
    response = api_client.post(
        path,
        content=b"x" * (maximum + 1),
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}


def test_soft_deleted_customer_rejects_edits_and_new_opportunities(
    api_client: TestClient,
    db_session: Session,
) -> None:
    customer = api_client.post(
        "/api/customers",
        json={"name": unique_label("Cliente eliminado")},
    ).json()
    opportunity = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer["id"], "source": "WEB"},
    ).json()

    assert api_client.delete(f"/api/customers/{customer['id']}").status_code == 204
    assert (
        api_client.patch(
            f"/api/customers/{customer['id']}",
            json={
                "phone": "11 5555 5555",
                "expected_updated_at": customer["updated_at"],
            },
        ).status_code
        == 409
    )
    assert (
        api_client.post(
            "/api/opportunities",
            json={"customer_id": customer["id"], "source": "WHATSAPP"},
        ).status_code
        == 409
    )
    assert api_client.get(f"/api/opportunities/{opportunity['id']}").status_code == 200

    persisted_opportunity = db_session.get(Opportunity, opportunity["id"])
    assert persisted_opportunity is not None
    persisted_opportunity.deleted_at = datetime.now(UTC)
    db_session.commit()

    assert api_client.get(f"/api/opportunities/{opportunity['id']}").status_code == 404
    listing = api_client.get(
        "/api/opportunities",
        params={"customer_id": customer["id"]},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 0


def test_inactive_product_is_historical_but_cannot_enter_a_new_quote(
    api_client: TestClient,
) -> None:
    customer = api_client.post(
        "/api/customers",
        json={"name": unique_label("Cliente producto histórico")},
    ).json()
    product = api_client.post(
        "/api/products",
        json={"name": unique_label("Producto histórico")},
    ).json()
    quoted_opportunity = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer["id"], "source": "WEB"},
    ).json()
    quote_payload = {
        "products": [{"product_id": product["id"], "quantity_kg": "500.000"}]
    }
    assert (
        api_client.post(
            f"/api/opportunities/{quoted_opportunity['id']}/quote",
            json=quote_payload,
        ).status_code
        == 200
    )
    assert (
        api_client.patch(
            f"/api/products/{product['id']}",
            json={"is_active": False},
        ).status_code
        == 200
    )
    assert (
        api_client.post(
            "/api/products",
            json={"name": f"  {product['name'].upper()}  "},
        ).status_code
        == 409
    )

    historical_detail = api_client.get(
        f"/api/opportunities/{quoted_opportunity['id']}"
    ).json()
    assert historical_detail["products"][0]["product"]["name"] == product["name"]
    assert Decimal(historical_detail["products"][0]["quantity_kg"]) == Decimal(
        "500.000"
    )
    changed_quantity = api_client.put(
        f"/api/opportunities/{quoted_opportunity['id']}/quote-products",
        json={
            "expected_updated_at": historical_detail["updated_at"],
            "products": [{"product_id": product["id"], "quantity_kg": "750.000"}],
        },
    )
    assert changed_quantity.status_code == 200

    new_opportunity = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer["id"], "source": "WHATSAPP"},
    ).json()
    assert (
        api_client.post(
            f"/api/opportunities/{new_opportunity['id']}/quote",
            json=quote_payload,
        ).status_code
        == 409
    )


def test_inactive_assignee_remains_visible_but_cannot_be_assigned_again(
    api_client: TestClient,
    supervisor_user: User,
) -> None:
    user = api_client.post(
        "/api/users",
        json={
            "full_name": "Vendedor histórico",
            "email": f"{unique_label('historical-user')}@faa.test",
            "password": "valid-test-password",
            "role": "VENDEDOR",
        },
    ).json()
    customer = api_client.post(
        "/api/customers",
        json={"name": unique_label("Cliente usuario histórico")},
    ).json()
    assigned = api_client.post(
        "/api/opportunities",
        json={
            "customer_id": customer["id"],
            "source": "WEB",
            "assigned_user_id": user["id"],
        },
    ).json()
    api_client.headers["Authorization"] = f"Bearer {create_access_token(user['id'])}"
    actor_opportunity = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer["id"], "source": "WHATSAPP"},
    ).json()
    api_client.headers["Authorization"] = (
        f"Bearer {create_access_token(supervisor_user.id)}"
    )
    assert (
        api_client.patch(
            f"/api/users/{user['id']}",
            json={"is_active": False},
        ).status_code
        == 200
    )

    detail = api_client.get(f"/api/opportunities/{assigned['id']}").json()
    assert detail["assigned_user"]["id"] == user["id"]
    assert detail["assigned_user"]["full_name"] == "Vendedor histórico"
    actor_detail = api_client.get(
        f"/api/opportunities/{actor_opportunity['id']}"
    ).json()
    assert actor_detail["history"][0]["changed_by_user_id"] == user["id"]

    unassigned = api_client.post(
        "/api/opportunities",
        json={"customer_id": customer["id"], "source": "WHATSAPP"},
    ).json()
    unassigned_detail = api_client.get(f"/api/opportunities/{unassigned['id']}").json()
    assert (
        api_client.put(
            f"/api/opportunities/{unassigned['id']}/assignee",
            json={
                "assigned_user_id": user["id"],
                "expected_updated_at": unassigned_detail["updated_at"],
            },
        ).status_code
        == 409
    )


def test_customer_update_rejects_stale_expected_updated_at(db_session: Session) -> None:
    service = CustomerService(db_session)
    customer = service.create_customer(
        name=unique_label("Cliente concurrente"),
        company=None,
        email=None,
        phone=None,
        province=None,
        legendary_historical_override=False,
    )
    original_updated_at = customer.updated_at
    service.update_customer(
        customer.id,
        {"phone": "11 4444 4444"},
        expected_updated_at=original_updated_at,
    )

    with pytest.raises(StaleWriteConflictError) as stale_write:
        service.update_customer(
            customer.id,
            {"province": "Buenos Aires"},
            expected_updated_at=original_updated_at,
        )

    assert stale_write.value.current_updated_at == customer.updated_at
    assert customer.phone == "11 4444 4444"


def test_crud_updates_are_atomic_and_advance_aware_timestamps(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    customer_service = CustomerService(db_session)
    product_service = ProductService(db_session)
    user_service = UserService(db_session)
    customer = customer_service.create_customer(
        name=f"Cliente timestamps {suffix}",
        company=None,
        email=None,
        phone=None,
        province=None,
        legendary_historical_override=False,
    )
    product = product_service.create_product(name=f"Producto timestamps {suffix}")
    first_user = user_service.create_user(
        full_name="Primer usuario rollback",
        email=f"first-{suffix}@faa.test",
        password="valid-test-password",
        role=UserRole.VENDEDOR,
    )
    second_user = user_service.create_user(
        full_name="Segundo usuario rollback",
        email=f"second-{suffix}@faa.test",
        password="valid-test-password",
        role=UserRole.VENDEDOR,
    )
    customer_updated_at = customer.updated_at
    product_updated_at = product.updated_at
    user_updated_at = first_user.updated_at

    customer_service.update_customer(customer.id, {"phone": "11 4444 4444"})
    product_service.update_product(product.id, {"name": f"Producto nuevo {suffix}"})
    user_service.update_user(first_user.id, {"full_name": "Usuario actualizado"})
    customer_id = customer.id
    product_id = product.id
    first_user_id = first_user.id
    first_user_email = first_user.email
    second_user_id = second_user.id
    with pytest.raises(DuplicateEntityError):
        user_service.update_user(
            second_user_id,
            {"email": first_user_email.upper(), "is_active": False},
        )
    with pytest.raises(IntegrityError):
        product_service.update_product(product_id, {"name": "   "})

    db_session.expire_all()
    persisted_customer = db_session.get(Customer, customer_id)
    persisted_product = db_session.get(Product, product_id)
    persisted_first_user = db_session.get(User, first_user_id)
    persisted_second_user = db_session.get(User, second_user_id)
    assert persisted_customer is not None
    assert persisted_product is not None
    assert persisted_first_user is not None
    assert persisted_second_user is not None
    assert persisted_customer.updated_at > customer_updated_at
    assert persisted_product.updated_at > product_updated_at
    assert persisted_first_user.updated_at > user_updated_at
    assert persisted_customer.updated_at.tzinfo is not None
    assert persisted_product.updated_at.tzinfo is not None
    assert persisted_first_user.updated_at.tzinfo is not None
    assert persisted_second_user.email == f"second-{suffix}@faa.test"
    assert persisted_second_user.is_active is True
    assert persisted_product.name == f"Producto nuevo {suffix}"


def test_default_orders_are_deterministic(db_session: Session) -> None:
    marker = unique_label("order-marker")
    customer_service = CustomerService(db_session)
    first_alpha = customer_service.create_customer(
        name="alpha",
        company=marker,
        email=None,
        phone=None,
        province=None,
        legendary_historical_override=False,
    )
    second_alpha = customer_service.create_customer(
        name="Alpha",
        company=marker,
        email=None,
        phone=None,
        province=None,
        legendary_historical_override=False,
    )
    beta = customer_service.create_customer(
        name="beta",
        company=marker,
        email=None,
        phone=None,
        province=None,
        legendary_historical_override=False,
    )
    customers, total = customer_service.list_customers(
        page=1,
        page_size=20,
        search=marker,
        include_deleted=False,
    )
    assert total == 3
    assert [customer.id for customer in customers] == [
        first_alpha.id,
        second_alpha.id,
        beta.id,
    ]

    common_time = datetime.now(UTC)
    opportunities = [
        Opportunity(
            customer_id=first_alpha.id,
            source=LeadSource.WEB,
            status=OpportunityStatus.NUEVA,
            current_status_entered_at=common_time,
            created_at=common_time,
            updated_at=common_time,
        )
        for _ in range(2)
    ]
    db_session.add_all(opportunities)
    db_session.commit()
    listed, opportunity_total = OpportunityQueryService(db_session).list_opportunities(
        page=1,
        page_size=20,
        status=None,
        customer_id=first_alpha.id,
        assigned_user_id=None,
        source=None,
    )
    assert opportunity_total == 2
    assert [opportunity.id for opportunity in listed] == [
        opportunities[1].id,
        opportunities[0].id,
    ]


def test_history_order_uses_id_as_timestamp_tiebreaker(
    db_session: Session,
) -> None:
    customer = Customer(name=unique_label("Cliente history order"))
    db_session.add(customer)
    db_session.commit()
    created_at = datetime.now(UTC)
    opportunity = Opportunity(
        customer_id=customer.id,
        source=LeadSource.WEB,
        status=OpportunityStatus.NEGOCIACION,
        current_status_entered_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(opportunity)
    db_session.commit()
    creation = OpportunityStatusHistory(
        opportunity_id=opportunity.id,
        from_status=None,
        to_status=OpportunityStatus.NUEVA,
        changed_at=created_at,
    )
    transition_time = created_at + timedelta(seconds=1)
    same_time_entries = [
        OpportunityStatusHistory(
            opportunity_id=opportunity.id,
            from_status=OpportunityStatus.NUEVA,
            to_status=OpportunityStatus.COTIZADA,
            changed_at=transition_time,
        ),
        OpportunityStatusHistory(
            opportunity_id=opportunity.id,
            from_status=OpportunityStatus.COTIZADA,
            to_status=OpportunityStatus.NEGOCIACION,
            changed_at=transition_time,
        ),
    ]
    db_session.add_all([creation, *same_time_entries])
    db_session.commit()
    db_session.expire_all()

    detail = OpportunityQueryService(db_session).get_detail(opportunity.id)
    assert [entry.id for entry in detail.status_history] == [
        creation.id,
        same_time_entries[0].id,
        same_time_entries[1].id,
    ]


def test_pipeline_query_eager_loads_summary_relations_without_n_plus_one(
    db_session: Session,
) -> None:
    suffix = uuid4().hex
    customer = Customer(name=f"Cliente eager {suffix}")
    user = User(
        full_name="Vendedor eager",
        email=f"eager-{suffix}@faa.test",
        password_hash=hash_password("valid-test-password"),
        role=UserRole.VENDEDOR,
    )
    product = Product(name=f"Producto eager {suffix}")
    db_session.add_all([customer, user, product])
    db_session.commit()
    opportunities = [
        Opportunity(
            customer_id=customer.id,
            assigned_user_id=user.id,
            source=LeadSource.WEB,
        )
        for _ in range(3)
    ]
    db_session.add_all(opportunities)
    db_session.commit()
    db_session.add_all(
        [
            OpportunityProduct(
                opportunity_id=opportunity.id,
                product_id=product.id,
                quantity_kg=Decimal("100.000"),
            )
            for opportunity in opportunities
        ]
    )
    db_session.commit()
    customer_id = customer.id
    customer_name = customer.name
    user_name = user.full_name
    product_name = product.name
    db_session.expire_all()

    statements: list[str] = []
    connection = db_session.get_bind()
    assert isinstance(connection, Connection)

    def capture_selects(
        _connection: Connection,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(connection, "before_cursor_execute", capture_selects)
    try:
        listed, total = OpportunityQueryService(db_session).list_opportunities(
            page=1,
            page_size=20,
            status=None,
            customer_id=customer_id,
            assigned_user_id=None,
            source=None,
        )
        query_count_after_load = len(statements)
        for opportunity in listed:
            assert opportunity.customer.name == customer_name
            assert opportunity.assigned_user is not None
            assert opportunity.assigned_user.full_name == user_name
            assert opportunity.opportunity_products[0].product.name == product_name
        assert len(statements) == query_count_after_load
    finally:
        event.remove(connection, "before_cursor_execute", capture_selects)

    assert total == 3
    assert query_count_after_load == 3
