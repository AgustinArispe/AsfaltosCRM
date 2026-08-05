import json
from datetime import UTC, datetime, timedelta
from typing import TypedDict

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from app.core.intake_security import build_web_intake_signature
from app.schemas import WebLeadIntakeResponse


class WebPayload(TypedDict, total=False):
    external_submission_id: str
    name: str
    company: str | None
    email: str | None
    phone: str | None
    province: str | None
    message: str | None
    source: str
    unexpected: str


def make_payload(external_submission_id: str = "web-api-submission") -> WebPayload:
    return {
        "external_submission_id": external_submission_id,
        "name": "Cliente Intake API",
        "company": "Constructora API",
        "email": "intake-api@ejemplo.com",
        "phone": "+54 11 4444-5555",
        "province": "Buenos Aires",
        "message": "Necesito una cotización",
    }


def encode_payload(payload: WebPayload) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def signed_headers(
    raw_body: bytes,
    *,
    timestamp: str | None = None,
) -> dict[str, str]:
    signed_at = timestamp or str(int(datetime.now(UTC).timestamp()))
    return {
        "Content-Type": "application/json",
        "X-FAA-Intake-Timestamp": signed_at,
        "X-FAA-Intake-Signature": build_web_intake_signature(
            signed_at,
            raw_body,
        ),
    }


def signed_post(
    client: TestClient,
    payload: WebPayload,
) -> Response:
    raw_body = encode_payload(payload)
    return client.post(
        "/api/intake/web",
        content=raw_body,
        headers=signed_headers(raw_body),
    )


def test_valid_hmac_creates_without_crm_jwt_and_replay_returns_200(
    api_client: TestClient,
) -> None:
    del api_client.headers["Authorization"]
    payload = make_payload("api-created-and-replayed")

    first_response = signed_post(api_client, payload)
    replay_response = signed_post(api_client, payload)
    first = WebLeadIntakeResponse.model_validate(first_response.json())
    replay = WebLeadIntakeResponse.model_validate(replay_response.json())

    assert first_response.status_code == 201
    assert first.created is True
    assert replay_response.status_code == 200
    assert replay.created is False
    assert replay.intake_id == first.intake_id
    assert replay.customer_id == first.customer_id
    assert replay.opportunity_id == first.opportunity_id


def test_same_id_with_different_payload_returns_409(api_client: TestClient) -> None:
    del api_client.headers["Authorization"]
    first = make_payload("api-idempotency-conflict")
    second = make_payload("api-idempotency-conflict")
    second["message"] = "Un mensaje diferente"

    assert signed_post(api_client, first).status_code == 201
    response = signed_post(api_client, second)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "External submission ID was already used with different data"
    }


@pytest.mark.parametrize("missing_header", ["timestamp", "signature"])
def test_missing_hmac_header_returns_generic_401(
    api_client: TestClient,
    missing_header: str,
) -> None:
    del api_client.headers["Authorization"]
    raw_body = encode_payload(make_payload(f"missing-{missing_header}"))
    headers = signed_headers(raw_body)
    header_name = (
        "X-FAA-Intake-Timestamp"
        if missing_header == "timestamp"
        else "X-FAA-Intake-Signature"
    )
    del headers[header_name]

    response = api_client.post(
        "/api/intake/web",
        content=raw_body,
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not authenticate intake request"}


def test_invalid_signature_and_altered_body_return_401(api_client: TestClient) -> None:
    del api_client.headers["Authorization"]
    original = encode_payload(make_payload("signed-original"))
    altered = encode_payload(make_payload("altered-after-signing"))
    invalid_headers = signed_headers(original)
    invalid_headers["X-FAA-Intake-Signature"] = "sha256=" + "0" * 64

    invalid = api_client.post(
        "/api/intake/web",
        content=original,
        headers=invalid_headers,
    )
    altered_response = api_client.post(
        "/api/intake/web",
        content=altered,
        headers=signed_headers(original),
    )

    assert invalid.status_code == 401
    assert altered_response.status_code == 401


def test_expired_timestamp_returns_401(api_client: TestClient) -> None:
    del api_client.headers["Authorization"]
    raw_body = encode_payload(make_payload("expired-timestamp"))
    expired = str(int((datetime.now(UTC) - timedelta(minutes=6)).timestamp()))

    response = api_client.post(
        "/api/intake/web",
        content=raw_body,
        headers=signed_headers(raw_body, timestamp=expired),
    )

    assert response.status_code == 401


@pytest.mark.parametrize("extra_field", ["source", "unexpected"])
def test_request_forbids_source_and_unknown_fields(
    api_client: TestClient,
    extra_field: str,
) -> None:
    del api_client.headers["Authorization"]
    payload = make_payload(f"extra-{extra_field}")
    if extra_field == "source":
        payload["source"] = "WHATSAPP"
    else:
        payload["unexpected"] = "not accepted"

    assert signed_post(api_client, payload).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"external_submission_id": "   ", "name": "Cliente"},
        {"external_submission_id": "valid-id", "name": "   "},
        {"external_submission_id": "x" * 201, "name": "Cliente"},
        {"external_submission_id": "valid-id", "name": "x" * 201},
        {
            "external_submission_id": "valid-id",
            "name": "Cliente",
            "message": "x" * 10_001,
        },
    ],
)
def test_request_enforces_required_values_and_size_limits(
    api_client: TestClient,
    payload: WebPayload,
) -> None:
    del api_client.headers["Authorization"]
    assert signed_post(api_client, payload).status_code == 422
