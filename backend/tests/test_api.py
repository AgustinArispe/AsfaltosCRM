from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Opportunity, Product, User, UserRole


def persist(db_session: Session, *entities: object) -> None:
    db_session.add_all(entities)
    db_session.commit()


def make_user(
    email: str = "api-user@faa.test",
    *,
    is_active: bool = True,
) -> User:
    return User(
        full_name="Usuario API",
        email=email,
        password_hash="hashed-password",
        role=UserRole.VENDEDOR,
        is_active=is_active,
    )


def create_customer(client: TestClient, name: str = "Cliente API") -> dict[str, object]:
    response = client.post(
        "/api/customers",
        json={"name": name, "company": "Constructora API"},
    )
    assert response.status_code == 201
    return response.json()


def create_product(client: TestClient, name: str = "Producto API") -> dict[str, object]:
    response = client.post("/api/products", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_opportunity(
    client: TestClient,
    customer_id: int,
    *,
    source: str = "WEB",
    assigned_user_id: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"customer_id": customer_id, "source": source}
    if assigned_user_id is not None:
        payload["assigned_user_id"] = assigned_user_id
    response = client.post("/api/opportunities", json=payload)
    assert response.status_code == 201
    return response.json()


def quote_opportunity(
    client: TestClient,
    opportunity_id: int,
    product_id: int,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "products": [{"product_id": product_id, "quantity_kg": 2500}]
    }
    response = client.post(
        f"/api/opportunities/{opportunity_id}/quote",
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_customer_crud_search_and_soft_delete(api_client: TestClient) -> None:
    first = api_client.post(
        "/api/customers",
        json={
            "name": "Constructora Austral",
            "company": "Austral SA",
            "email": "ventas@austral.test",
            "phone": "1122334455",
            "province": "Buenos Aires",
            "legendary_historical_override": True,
        },
    )
    second = api_client.post(
        "/api/customers",
        json={"name": "Cliente Norte", "phone": "99887766"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    customer_id = first.json()["id"]

    listing = api_client.get(
        "/api/customers",
        params={"search": "austral", "page": 1, "page_size": 1},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["page"] == 1
    assert listing.json()["page_size"] == 1
    assert listing.json()["items"][0]["id"] == customer_id

    detail = api_client.get(f"/api/customers/{customer_id}")
    assert detail.status_code == 200
    assert "opportunities" not in detail.json()

    updated = api_client.patch(
        f"/api/customers/{customer_id}",
        json={"company": None, "province": "Neuquén"},
    )
    assert updated.status_code == 200
    assert updated.json()["company"] is None
    assert updated.json()["province"] == "Neuquén"

    deleted = api_client.delete(f"/api/customers/{customer_id}")
    repeated_delete = api_client.delete(f"/api/customers/{customer_id}")
    assert deleted.status_code == 204
    assert repeated_delete.status_code == 204

    active_listing = api_client.get("/api/customers")
    all_listing = api_client.get(
        "/api/customers",
        params={"include_deleted": True},
    )
    assert active_listing.json()["total"] == 1
    assert all_listing.json()["total"] == 2
    assert api_client.get(f"/api/customers/{customer_id}").status_code == 404


def test_customer_request_validation_and_forbidden_internal_fields(
    api_client: TestClient,
) -> None:
    assert api_client.post("/api/customers", json={"name": "   "}).status_code == 422
    response = api_client.post(
        "/api/customers",
        json={"name": "Cliente", "id": 999, "deleted_at": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_customer_pagination_limits(api_client: TestClient) -> None:
    for index in range(3):
        create_customer(api_client, name=f"Cliente paginado {index}")

    page = api_client.get(
        "/api/customers",
        params={"page": 2, "page_size": 2},
    )
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 1
    assert api_client.get("/api/customers", params={"page": 0}).status_code == 422
    assert (
        api_client.get("/api/customers", params={"page_size": 101}).status_code
        == 422
    )


def test_products_create_unique_list_and_deactivate(api_client: TestClient) -> None:
    first = create_product(api_client, "SuperPhalt API")
    second = create_product(api_client, "Bituplast API")

    duplicate = api_client.post(
        "/api/products",
        json={"name": "  superphalt api "},
    )
    assert duplicate.status_code == 409

    update = api_client.patch(
        f"/api/products/{first['id']}",
        json={"name": "SuperPhalt actualizado", "is_active": False},
    )
    assert update.status_code == 200
    assert update.json()["is_active"] is False

    active = api_client.get("/api/products")
    all_products = api_client.get(
        "/api/products",
        params={"include_inactive": True},
    )
    assert [product["id"] for product in active.json()] == [second["id"]]
    assert {product["id"] for product in all_products.json()} == {
        first["id"],
        second["id"],
    }


def test_product_validation_and_not_found(api_client: TestClient) -> None:
    assert api_client.post("/api/products", json={"name": ""}).status_code == 422
    assert (
        api_client.patch("/api/products/999999999", json={"is_active": False}).status_code
        == 404
    )


def test_opportunity_create_detail_assignee_and_history(
    api_client: TestClient,
    db_session: Session,
) -> None:
    user = make_user()
    persist(db_session, user)
    customer = create_customer(api_client)

    opportunity = create_opportunity(
        api_client,
        customer["id"],
        source="WHATSAPP",
        assigned_user_id=user.id,
    )

    assert opportunity["status"] == "NUEVA"
    assert opportunity["assigned_user"]["id"] == user.id
    assert opportunity["products"] == []
    assert opportunity["history"][0]["from_status"] is None
    assert opportunity["history"][0]["to_status"] == "NUEVA"
    assert api_client.get(f"/api/opportunities/{opportunity['id']}").status_code == 200


def test_opportunity_create_rejects_missing_customer_and_inactive_assignee(
    api_client: TestClient,
    db_session: Session,
) -> None:
    missing_customer = api_client.post(
        "/api/opportunities",
        json={"customer_id": 999999999, "source": "WEB"},
    )
    assert missing_customer.status_code == 404

    customer = create_customer(api_client)
    user = make_user(is_active=False)
    persist(db_session, user)
    inactive_user = api_client.post(
        "/api/opportunities",
        json={
            "customer_id": customer["id"],
            "source": "WEB",
            "assigned_user_id": user.id,
        },
    )
    assert inactive_user.status_code == 409


def test_opportunity_list_and_filters(
    api_client: TestClient,
    db_session: Session,
) -> None:
    user = make_user()
    persist(db_session, user)
    first_customer = create_customer(api_client, "Cliente filtros 1")
    second_customer = create_customer(api_client, "Cliente filtros 2")
    first = create_opportunity(
        api_client,
        first_customer["id"],
        source="WEB",
        assigned_user_id=user.id,
    )
    create_opportunity(api_client, second_customer["id"], source="WHATSAPP")

    response = api_client.get(
        "/api/opportunities",
        params={
            "status": "NUEVA",
            "customer_id": first_customer["id"],
            "assigned_user_id": user.id,
            "source": "WEB",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == first["id"]


def test_complete_won_flow_and_detail_history(
    api_client: TestClient,
    supervisor_user: User,
) -> None:
    actor_id = supervisor_user.id
    customer = create_customer(api_client, "Cliente ganado")
    product = create_product(api_client, "Producto ganado")
    opportunity = create_opportunity(api_client, customer["id"])
    opportunity_id = opportunity["id"]

    quoted = quote_opportunity(
        api_client,
        opportunity_id,
        product["id"],
    )
    negotiation = api_client.post(
        f"/api/opportunities/{opportunity_id}/move-to-negotiation",
        json={},
    )
    won = api_client.post(
        f"/api/opportunities/{opportunity_id}/win",
        json={},
    )
    detail = api_client.get(f"/api/opportunities/{opportunity_id}")

    assert quoted["status"] == "COTIZADA"
    assert negotiation.status_code == 200
    assert negotiation.json()["status"] == "NEGOCIACION"
    assert won.status_code == 200
    assert won.json()["status"] == "GANADA"
    assert [entry["to_status"] for entry in detail.json()["history"]] == [
        "NUEVA",
        "COTIZADA",
        "NEGOCIACION",
        "GANADA",
    ]
    assert all(
        entry["changed_by_user_id"] == actor_id
        for entry in detail.json()["history"][1:]
    )


def test_lost_opportunity_flow(api_client: TestClient) -> None:
    customer = create_customer(api_client, "Cliente perdido")
    opportunity = create_opportunity(api_client, customer["id"])

    response = api_client.post(
        f"/api/opportunities/{opportunity['id']}/lose",
        json={"loss_reason": "PRECIO"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PERDIDA"
    assert response.json()["loss_reason"] == "PRECIO"
    assert response.json()["history"][-1]["to_status"] == "PERDIDA"


def test_update_quote_products_and_unassign_user(
    api_client: TestClient,
    db_session: Session,
) -> None:
    user = make_user()
    persist(db_session, user)
    customer = create_customer(api_client, "Cliente edición")
    first_product = create_product(api_client, "Producto edición 1")
    second_product = create_product(api_client, "Producto edición 2")
    opportunity = create_opportunity(
        api_client,
        customer["id"],
        assigned_user_id=user.id,
    )
    quote_opportunity(api_client, opportunity["id"], first_product["id"])

    update = api_client.put(
        f"/api/opportunities/{opportunity['id']}/quote-products",
        json={
            "products": [
                {"product_id": second_product["id"], "quantity_kg": "875.500"}
            ]
        },
    )
    unassigned = api_client.put(
        f"/api/opportunities/{opportunity['id']}/assignee",
        json={"assigned_user_id": None},
    )

    assert update.status_code == 200
    assert update.json()["products"][0]["product"]["id"] == second_product["id"]
    assert Decimal(update.json()["products"][0]["quantity_kg"]) == Decimal(
        "875.500"
    )
    assert len(update.json()["history"]) == 2
    assert unassigned.status_code == 200
    assert unassigned.json()["assigned_user"] is None


def test_opportunity_domain_and_product_errors_are_translated(
    api_client: TestClient,
) -> None:
    customer = create_customer(api_client, "Cliente errores")
    inactive_product = create_product(api_client, "Producto inactivo API")
    api_client.patch(
        f"/api/products/{inactive_product['id']}",
        json={"is_active": False},
    )
    opportunity = create_opportunity(api_client, customer["id"])

    invalid_transition = api_client.post(
        f"/api/opportunities/{opportunity['id']}/win"
    )
    inactive_quote = api_client.post(
        f"/api/opportunities/{opportunity['id']}/quote",
        json={
            "products": [
                {"product_id": inactive_product["id"], "quantity_kg": 100}
            ]
        },
    )
    empty_quote = api_client.post(
        f"/api/opportunities/{opportunity['id']}/quote",
        json={"products": []},
    )

    assert invalid_transition.status_code == 409
    assert inactive_quote.status_code == 409
    assert empty_quote.status_code == 422


def test_opportunity_request_validation_and_not_found(api_client: TestClient) -> None:
    invalid_source = api_client.post(
        "/api/opportunities",
        json={"customer_id": 1, "source": "META"},
    )
    invalid_quantity = api_client.post(
        "/api/opportunities/1/quote",
        json={"products": [{"product_id": 1, "quantity_kg": 0}]},
    )

    assert invalid_source.status_code == 422
    assert invalid_quantity.status_code == 422
    assert api_client.get("/api/opportunities/999999999").status_code == 404


def test_soft_deleted_records_remain_persisted_but_hidden(
    api_client: TestClient,
    db_session: Session,
) -> None:
    customer = create_customer(api_client, "Cliente histórico")
    opportunity = create_opportunity(api_client, customer["id"])

    assert api_client.delete(f"/api/customers/{customer['id']}").status_code == 204

    persisted_customer = db_session.get(Customer, customer["id"])
    persisted_opportunity = db_session.scalar(
        select(Opportunity).where(Opportunity.id == opportunity["id"])
    )
    assert persisted_customer is not None
    assert persisted_customer.deleted_at is not None
    assert persisted_opportunity is not None


def test_openapi_exposes_crm_routes(api_client: TestClient) -> None:
    response = api_client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/customers" in paths
    assert "/api/products" in paths
    assert "/api/opportunities/{opportunity_id}/quote" in paths
    assert "/api/opportunities/{opportunity_id}/win" in paths
