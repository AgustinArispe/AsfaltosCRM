from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    LeadSource,
    Opportunity,
    OpportunityStatus,
    Product,
    User,
)
from app.services.opportunity_service import OpportunityService


def setup_opportunity(session: Session) -> tuple[Opportunity, Product]:
    customer = Customer(name=f"Cliente de seguimiento {uuid4().hex}")
    product = Product(name=f"Producto de seguimiento {uuid4().hex}")
    session.add_all([customer, product])
    session.commit()
    opportunity = OpportunityService(session).create_opportunity(
        customer_id=customer.id, source=LeadSource.REFERIDO
    )
    return opportunity, product


@pytest.mark.parametrize(
    "payload", [{}, {"note": ""}, {"note": "   \n "}, {"note": "x" * 4001}]
)
def test_prepare_rejects_missing_or_blank_note_without_changing_anything(
    api_client: TestClient,
    db_session: Session,
    payload: dict[str, str],
) -> None:
    opportunity, _ = setup_opportunity(db_session)
    before = api_client.get(f"/api/opportunities/{opportunity.id}").json()
    response = api_client.post(
        f"/api/opportunities/{opportunity.id}/prepare-quote", json=payload
    )
    assert response.status_code == 422
    assert api_client.get(f"/api/opportunities/{opportunity.id}").json() == before


def test_complete_flow_records_notes_atomically_and_lists_only_customer_notes(
    api_client: TestClient,
    db_session: Session,
    supervisor_user: User,
) -> None:
    opportunity, product = setup_opportunity(db_session)
    other, _ = setup_opportunity(db_session)
    other_customer_id = other.customer_id
    base = f"/api/opportunities/{opportunity.id}"
    quoted_payload = {
        "products": [{"product_id": product.id, "quantity_kg": "1250.500"}],
        "note": "Se envió la cotización solicitada",
    }
    assert api_client.post(f"{base}/quote", json=quoted_payload).status_code == 409
    prepared = api_client.post(
        f"{base}/prepare-quote", json={"note": "  Revisar el pedido del cliente  "}
    )
    assert prepared.status_code == 200
    assert prepared.json()["status"] == "PARA_COTIZAR"
    assert prepared.json()["products"] == []
    assert prepared.json()["history"][-1]["note"] == "Revisar el pedido del cliente"
    assert (
        api_client.post(
            f"{base}/quote", json={"products": [], "note": "No debe guardarse"}
        ).status_code
        == 422
    )
    assert api_client.get(base).json()["history"] == prepared.json()["history"]
    quoted = api_client.post(f"{base}/quote", json=quoted_payload)
    assert quoted.status_code == 200
    assert quoted.json()["status"] == "COTIZADA"
    assert api_client.post(f"{base}/win", json={}).status_code == 422
    won = api_client.post(f"{base}/win", json={"note": "El cliente confirmó la compra"})
    assert won.status_code == 200
    assert [entry["to_status"] for entry in won.json()["history"]] == [
        "NUEVA",
        "PARA_COTIZAR",
        "COTIZADA",
        "GANADA",
    ]
    assert all(
        entry["changed_by_user_id"] == supervisor_user.id
        for entry in won.json()["history"][1:]
    )
    notes = api_client.get(
        f"/api/customers/{opportunity.customer_id}/stage-notes?page_size=2"
    ).json()
    assert notes["total"] == 3
    assert len(notes["items"]) == 2
    assert notes["items"][0]["note"] == "El cliente confirmó la compra"
    assert notes["items"][0]["author_name"] == supervisor_user.full_name
    assert notes["items"][0]["opportunity_id"] == opportunity.id
    assert (
        api_client.get(f"/api/customers/{other_customer_id}/stage-notes").json()[
            "items"
        ]
        == []
    )
    assert (
        api_client.get(
            f"/api/customers/{opportunity.customer_id}/stage-notes?page=2&page_size=2"
        ).json()["items"][0]["note"]
        == "Revisar el pedido del cliente"
    )


def test_regression_loss_and_reopen_keep_quotes_and_require_their_own_note(
    api_client: TestClient,
    db_session: Session,
) -> None:
    opportunity, product = setup_opportunity(db_session)
    base = f"/api/opportunities/{opportunity.id}"
    api_client.post(f"{base}/prepare-quote", json={"note": "Preparar propuesta"})
    api_client.post(
        f"{base}/quote",
        json={
            "note": "Propuesta enviada",
            "products": [{"product_id": product.id, "quantity_kg": 100}],
        },
    )
    assert (
        api_client.post(
            f"{base}/regress",
            json={"expected_status": "COTIZADA", "target_status": "PARA_COTIZAR"},
        ).status_code
        == 422
    )
    regressed = api_client.post(
        f"{base}/regress",
        json={
            "expected_status": "COTIZADA",
            "target_status": "PARA_COTIZAR",
            "note": "El cliente solicitó revisar cantidades",
        },
    )
    assert regressed.status_code == 200
    assert regressed.json()["products"]
    assert (
        api_client.post(f"{base}/lose", json={"loss_reason": "PRECIO"}).status_code
        == 422
    )
    assert (
        api_client.post(
            f"{base}/lose",
            json={"loss_reason": "PRECIO", "note": "El precio no fue aceptado"},
        ).status_code
        == 200
    )
    command = {
        "command_id": str(uuid4()),
        "expected_status": "PERDIDA",
        "note": "El cliente retoma la propuesta",
    }
    reopened = api_client.post(f"{base}/reopen", json=command)
    assert reopened.status_code == 200
    assert reopened.json()["status"] == OpportunityStatus.COTIZADA
    assert (
        api_client.post(f"{base}/reopen", json=command).json()["history"]
        == reopened.json()["history"]
    )
    assert (
        api_client.post(
            f"{base}/reopen",
            json={**command, "note": "Otra nota para el mismo comando"},
        ).status_code
        == 409
    )
    assert (
        api_client.post(
            f"{base}/move-to-negotiation", json={"note": "Ruta retirada"}
        ).status_code
        == 404
    )


def test_prequote_without_products_can_be_lost_but_cannot_reopen_as_quoted(
    api_client: TestClient,
    db_session: Session,
) -> None:
    opportunity, _ = setup_opportunity(db_session)
    base = f"/api/opportunities/{opportunity.id}"
    api_client.post(f"{base}/prepare-quote", json={"note": "Esperamos las cantidades"})
    assert (
        api_client.post(
            f"{base}/lose",
            json={
                "loss_reason": "SIN_RESPUESTA",
                "note": "No respondió al seguimiento",
            },
        ).status_code
        == 200
    )
    assert (
        api_client.post(
            f"{base}/reopen",
            json={
                "command_id": str(uuid4()),
                "expected_status": "PERDIDA",
                "note": "No tiene productos cotizados",
            },
        ).status_code
        == 422
    )
