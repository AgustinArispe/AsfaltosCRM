import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.intake_security import build_web_intake_signature
from app.schemas import WebLeadIntakeRequest, WebLeadIntakeResponse

CONFIRMATION = "I-CONFIRM-SYNTHETIC-PRODUCTION-INTAKE"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a safe WordPress intake smoke test"
    )
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--confirm-production", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=15)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    if args.confirm_production != CONFIRMATION:
        print("Production confirmation phrase is invalid")
        return 2
    if not args.endpoint.startswith("https://") or not args.endpoint.endswith(
        "/api/intake/web"
    ):
        print("Endpoint must be the HTTPS production /api/intake/web URL")
        return 2
    secret = getenv("WEB_INTAKE_SIGNING_SECRET")
    if secret is None or len(secret) < 32:
        print("WEB_INTAKE_SIGNING_SECRET is not safely configured")
        return 2
    external_id = f"crm012-smoke-{uuid4()}"
    payload = WebLeadIntakeRequest(
        external_submission_id=external_id,
        name="CRM Production Smoke Test",
        company="FAA SYNTHETIC TEST - DELETE VIA CRM",
        email=None,
        phone=None,
        province="TEST",
        message="Synthetic operational smoke test; not a customer inquiry.",
    )
    raw_body = payload.model_dump_json().encode()
    timestamp = str(int(datetime.now(UTC).timestamp()))
    signature = build_web_intake_signature(timestamp, raw_body, secret=secret)
    request = Request(
        args.endpoint,
        data=raw_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-FAA-Intake-Timestamp": timestamp,
            "X-FAA-Intake-Signature": signature,
        },
    )
    try:
        with urlopen(request, timeout=args.timeout_seconds) as response:
            result = WebLeadIntakeResponse.model_validate_json(response.read())
            status_code = response.status
    except HTTPError as error:
        print(f"WordPress intake smoke failed with HTTP {error.code}")
        return 1
    except (URLError, TimeoutError):
        print("WordPress intake smoke failed with a transport error")
        return 1
    if status_code != 201 or not result.created:
        print("WordPress intake smoke returned an unexpected contract result")
        return 1
    print(
        "WordPress intake smoke passed; "
        f"opportunity_id={result.opportunity_id} cleanup_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
