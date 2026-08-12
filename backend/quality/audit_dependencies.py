"""Audit the exact locked dependency graph with reviewed, expiring exceptions."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

LOCKED_REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")


class AuditException(BaseModel):
    """A time-bounded, reviewed exception for one exact locked package."""

    model_config = ConfigDict(extra="forbid")

    advisory_id: str
    package: str
    version: str
    justification: str
    tracking_url: HttpUrl
    owner: str
    approved_on: date
    expires_on: date


class ExceptionRegistry(BaseModel):
    """Versioned exception registry."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    exceptions: list[AuditException]


class Vulnerability(BaseModel):
    """Relevant fields from one pip-audit vulnerability result."""

    model_config = ConfigDict(extra="ignore")

    id: str
    fix_versions: list[str]
    aliases: list[str] = Field(default_factory=list)


class AuditedPackage(BaseModel):
    """Relevant fields from one pip-audit package result."""

    model_config = ConfigDict(extra="ignore")

    name: str
    version: str
    vulns: list[Vulnerability]


class AuditReport(BaseModel):
    """Typed pip-audit JSON report."""

    model_config = ConfigDict(extra="ignore")

    dependencies: list[AuditedPackage]


def normalize_package_name(name: str) -> str:
    """Normalize a package name using Python packaging comparison rules."""

    return re.sub(r"[-_.]+", "-", name).lower()


def read_locked_packages(paths: list[Path]) -> set[tuple[str, str]]:
    """Return normalized package/version pairs from compiled lock files."""

    packages: set[tuple[str, str]] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = LOCKED_REQUIREMENT.match(line)
            if match is not None:
                packages.add((normalize_package_name(match.group(1)), match.group(2)))
    return packages


def load_exception_registry(path: Path) -> ExceptionRegistry:
    """Load and strictly validate the exception registry structure."""

    raw_registry: object = tomllib.loads(path.read_text(encoding="utf-8"))
    registry = ExceptionRegistry.model_validate(raw_registry)
    if registry.schema_version != 1:
        raise ValueError(f"Unsupported exception schema: {registry.schema_version}")
    return registry


def validate_exceptions(
    registry: ExceptionRegistry,
    locked_packages: set[tuple[str, str]],
    *,
    today: date,
) -> list[AuditException]:
    """Fail closed for stale or lock-mismatched vulnerability exceptions."""

    advisory_ids: set[str] = set()
    for exception in registry.exceptions:
        package_key = (normalize_package_name(exception.package), exception.version)
        if exception.advisory_id in advisory_ids:
            raise ValueError(f"Duplicate advisory exception: {exception.advisory_id}")
        if exception.expires_on < today:
            raise ValueError(f"Expired advisory exception: {exception.advisory_id}")
        if exception.expires_on < exception.approved_on:
            raise ValueError(
                f"Exception expires before approval: {exception.advisory_id}"
            )
        if package_key not in locked_packages:
            raise ValueError(
                "Exception package/version is not locked: "
                f"{exception.package}=={exception.version}"
            )
        advisory_ids.add(exception.advisory_id)
    return registry.exceptions


def print_audit_report(path: Path) -> None:
    """Render the machine-readable scanner output as concise reviewable text."""

    if not path.exists():
        return
    raw_report: object = json.loads(path.read_text(encoding="utf-8"))
    report = AuditReport.model_validate(raw_report)
    findings = [
        (package, vulnerability)
        for package in report.dependencies
        for vulnerability in package.vulns
    ]
    if not findings:
        print("pip-audit found no known vulnerabilities.")
        return
    print(f"pip-audit found {len(findings)} known vulnerability finding(s):")
    for package, vulnerability in findings:
        fixes = ", ".join(vulnerability.fix_versions) or "no published fix"
        print(
            f"- {vulnerability.id}: {package.name}=={package.version}; fixes: {fixes}"
        )


def run_audit(
    *,
    locks: list[Path],
    exception_file: Path,
    output_file: Path,
) -> int:
    """Validate exceptions, run pip-audit, and preserve its exit status."""

    locked_packages = read_locked_packages(locks)
    registry = load_exception_registry(exception_file)
    exceptions = validate_exceptions(registry, locked_packages, today=date.today())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--disable-pip",
        "--require-hashes",
        "--strict",
        "--format",
        "json",
        "--output",
        str(output_file),
    ]
    for lock in locks:
        command.extend(("--requirement", str(lock)))
    for exception in exceptions:
        print(
            "Active vulnerability exception: "
            f"{exception.advisory_id} for {exception.package}=={exception.version}; "
            f"expires {exception.expires_on.isoformat()}"
        )
        command.extend(("--ignore-vuln", exception.advisory_id))

    completed = subprocess.run(command, check=False)
    print_audit_report(output_file)
    return completed.returncode


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/pip-audit.json"),
        help="Path for the machine-readable pip-audit report.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the locked dependency audit."""

    args = parse_args()
    backend_directory = Path(__file__).resolve().parents[1]
    return run_audit(
        locks=[
            backend_directory / "requirements.lock",
            backend_directory / "requirements-dev.lock",
        ],
        exception_file=backend_directory / "pip-audit-exceptions.toml",
        output_file=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
