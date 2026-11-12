from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Customer, LeadSource, Opportunity, Product
from app.services.errors import InvalidTransitionNoteError
from app.services.opportunity_service import OpportunityService, QuoteProductInput


def prepared_opportunity(session: Session) -> tuple[Opportunity, Product]:
    customer = Customer(name=f"Provincia {uuid4().hex}")
    product = Product(name=f"Producto {uuid4().hex}")
    session.add_all([customer, product])
    session.commit()
    service = OpportunityService(session)
    opportunity = service.create_opportunity(
        customer_id=customer.id, source=LeadSource.REFERIDO
    )
    service.prepare_quote(opportunity.id, note="Se prepara la propuesta")
    return opportunity, product


@pytest.mark.parametrize("complete_at", ["quote", "win"])
@pytest.mark.parametrize("province", [None, "", "   ", "  Córdoba  "])
def test_province_is_optional_on_quote_and_win_and_persists_on_customer(
    api_client: TestClient, db_session: Session, complete_at: str, province: str | None
) -> None:
    opportunity, product = prepared_opportunity(db_session)
    base = f"/api/opportunities/{opportunity.id}"
    quote = api_client.post(
        f"{base}/quote",
        json={
            "note": "Cotización enviada",
            "products": [{"product_id": product.id, "quantity_kg": 250}],
            "province": province if complete_at == "quote" else None,
        },
    )
    assert quote.status_code == 200
    won = api_client.post(
        f"{base}/win",
        json={
            "note": "Compra confirmada",
            "province": province if complete_at == "win" else None,
        },
    )
    assert won.status_code == 200
    expected = province.strip() or None if province is not None else None
    assert won.json()["customer"]["province"] == expected
    assert (
        api_client.get(f"/api/customers/{opportunity.customer_id}").json()["province"]
        == expected
    )


def test_stage_completion_preserves_a_province_added_after_a_cached_customer_snapshot(
    api_client: TestClient, db_session: Session
) -> None:
    opportunity, product = prepared_opportunity(db_session)
    customer = db_session.get(Customer, opportunity.customer_id)
    assert customer is not None and customer.province is None
    db_session.execute(
        update(Customer)
        .where(Customer.id == customer.id)
        .values(province="Mendoza")
        .execution_options(synchronize_session=False)
    )
    db_session.commit()
    assert customer.province is None
    quoted = api_client.post(
        f"/api/opportunities/{opportunity.id}/quote",
        json={
            "note": "Propuesta enviada",
            "province": "Córdoba",
            "products": [{"product_id": product.id, "quantity_kg": 250}],
        },
    )
    assert quoted.status_code == 200
    assert quoted.json()["customer"]["province"] == "Mendoza"
    won = api_client.post(
        f"/api/opportunities/{opportunity.id}/win",
        json={"note": "Confirmada", "province": "Buenos Aires"},
    )
    assert won.status_code == 200
    assert won.json()["customer"]["province"] == "Mendoza"


def test_invalid_transition_or_quote_does_not_fill_province(
    api_client: TestClient, db_session: Session
) -> None:
    opportunity, product = prepared_opportunity(db_session)
    base = f"/api/opportunities/{opportunity.id}"
    before = api_client.get(base).json()
    product_id = product.id
    db_session.commit()
    assert (
        api_client.post(
            f"{base}/win", json={"note": "No corresponde", "province": "Salta"}
        ).status_code
        == 409
    )
    assert (
        api_client.post(
            f"{base}/quote",
            json={
                "note": "Inválida",
                "province": "Salta",
                "products": [{"product_id": product_id + 1000000, "quantity_kg": 10}],
            },
        ).status_code
        == 404
    )
    assert api_client.get(base).json() == before


def test_failed_history_note_rolls_back_province_and_quote_in_the_same_transaction(
    api_client: TestClient, db_session: Session
) -> None:
    opportunity, product = prepared_opportunity(db_session)
    opportunity_id = opportunity.id
    with pytest.raises(InvalidTransitionNoteError):
        OpportunityService(db_session).quote_opportunity(
            opportunity.id,
            [QuoteProductInput(product_id=product.id, quantity_kg=Decimal("100"))],
            note="   ",
            province="Salta",
        )
    detail = api_client.get(f"/api/opportunities/{opportunity_id}").json()
    assert detail["customer"]["province"] is None
    assert detail["status"] == "PARA_COTIZAR"
    assert detail["products"] == []
    assert len(detail["history"]) == 2
