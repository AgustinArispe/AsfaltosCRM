from datetime import date
from pathlib import Path

import pytest
from pydantic import HttpUrl

from quality.audit_dependencies import (
    AuditException,
    ExceptionRegistry,
    load_exception_registry,
    validate_exceptions,
)


def make_exception(*, expires_on: date, version: str = "1.0.0") -> AuditException:
    return AuditException(
        advisory_id="PYSEC-2099-1",
        package="example-package",
        version=version,
        justification="Not reachable in the deployed execution path.",
        tracking_url=HttpUrl("https://example.com/security/1"),
        owner="FAA CRM team",
        approved_on=date(2099, 1, 1),
        expires_on=expires_on,
    )


def test_committed_vulnerability_registry_has_no_silent_exceptions() -> None:
    """CRM-015 AC-03: the initial exception registry is explicit and empty."""

    registry = load_exception_registry(
        Path(__file__).resolve().parents[1] / "pip-audit-exceptions.toml"
    )

    assert registry.schema_version == 1
    assert registry.exceptions == []


def test_vulnerability_exception_must_match_locked_package_version() -> None:
    """CRM-015 AC-03: exceptions fail closed when the lock graph changes."""

    registry = ExceptionRegistry(
        schema_version=1,
        exceptions=[make_exception(expires_on=date(2099, 3, 1))],
    )

    with pytest.raises(ValueError, match="is not locked"):
        validate_exceptions(
            registry,
            {("example-package", "2.0.0")},
            today=date(2099, 2, 1),
        )


def test_vulnerability_exception_must_not_be_expired() -> None:
    """CRM-015 AC-03: expired vulnerability exceptions fail the gate."""

    registry = ExceptionRegistry(
        schema_version=1,
        exceptions=[make_exception(expires_on=date(2099, 1, 31))],
    )

    with pytest.raises(ValueError, match="Expired advisory"):
        validate_exceptions(
            registry,
            {("example-package", "1.0.0")},
            today=date(2099, 2, 1),
        )
