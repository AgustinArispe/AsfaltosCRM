import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from io import StringIO
from pathlib import PurePath
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Customer,
    CustomerImportAction,
    CustomerImportBatch,
    CustomerImportIssue,
    CustomerImportIssueCode,
    CustomerImportResult,
    CustomerImportRow,
    CustomerImportStatus,
)
from app.schemas.common import validate_email_format
from app.services.customer_identity_service import (
    CustomerIdentityResolver,
    acquire_advisory_locks,
    comparable_phone,
    customer_identity_locks,
    normalize_email,
    normalize_optional_text,
)
from app.services.customer_profile_service import (
    CustomerProfileInput,
    create_customer_from_profile,
    customer_would_be_enriched,
    enrich_customer_missing_fields,
)
from app.services.errors import (
    EntityNotFoundError,
    IdempotencyConflictError,
    InvalidCustomerImportError,
)

CSV_HEADER = ("name", "company", "email", "phone", "province")
MAX_IMPORT_BYTES = 2_000_000
MAX_IMPORT_ROWS = 5_000
MAX_FIELD_CHARS = 500


@dataclass(slots=True)
class _ParsedRow:
    row_number: int
    profile: CustomerProfileInput
    phone_match_key: str | None
    action: CustomerImportAction = CustomerImportAction.ERROR
    resolved_customer_id: int | None = None
    issue_code: CustomerImportIssueCode | None = None
    issue_field: str | None = None
    issue_message: str | None = None


@dataclass(frozen=True, slots=True)
class ImportCommitProjection:
    batch_id: int
    status: CustomerImportStatus
    created_count: int
    enriched_count: int
    unchanged_count: int
    customer_ids: tuple[int, ...]
    committed_at: datetime


class CustomerImportService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def dry_run(
        self,
        *,
        client_import_id: UUID,
        filename: str,
        content: bytes,
        actor_user_id: int,
    ) -> CustomerImportBatch:
        digest = sha256(content).hexdigest()
        sanitized_filename = PurePath(filename or "customers.csv").name[:255]
        parsed_rows = (
            self._parse(content)
            if sanitized_filename.lower().endswith(".csv")
            else [_file_error("Customer import file must use the .csv extension")]
        )
        with self._session.begin():
            acquire_advisory_locks(
                self._session, (("customer-import", str(client_import_id)),)
            )
            existing = self._session.scalar(
                select(CustomerImportBatch).where(
                    CustomerImportBatch.client_import_id == client_import_id
                )
            )
            if existing is not None:
                if (
                    existing.file_sha256 != digest
                    or existing.source_filename != sanitized_filename
                ):
                    raise IdempotencyConflictError(
                        "Customer import UUID was reused with another file"
                    )
                return self._load_batch(existing.id)
            self._resolve_preview_rows(parsed_rows)
            counts = {
                action: sum(row.action is action for row in parsed_rows)
                for action in CustomerImportAction
            }
            batch = CustomerImportBatch(
                client_import_id=client_import_id,
                file_sha256=digest,
                source_filename=sanitized_filename,
                status=(
                    CustomerImportStatus.INVALID
                    if counts[CustomerImportAction.ERROR]
                    else CustomerImportStatus.VALID
                ),
                version=1,
                actor_user_id=actor_user_id,
                row_count=sum(row.row_number > 0 for row in parsed_rows),
                create_count=counts[CustomerImportAction.CREATE],
                enrich_count=counts[CustomerImportAction.ENRICH],
                unchanged_count=counts[CustomerImportAction.UNCHANGED],
                error_count=counts[CustomerImportAction.ERROR],
            )
            self._session.add(batch)
            self._session.flush()
            for parsed in parsed_rows:
                row = CustomerImportRow(
                    batch_id=batch.id,
                    row_number=parsed.row_number,
                    name=parsed.profile.name,
                    company=parsed.profile.company,
                    email=parsed.profile.email,
                    phone=parsed.profile.phone,
                    phone_match_key=parsed.phone_match_key,
                    province=parsed.profile.province,
                    action=parsed.action,
                    resolved_customer_id=parsed.resolved_customer_id,
                )
                self._session.add(row)
                self._session.flush()
                if parsed.issue_code is not None and parsed.issue_message is not None:
                    self._session.add(
                        CustomerImportIssue(
                            row_id=row.id,
                            field_name=parsed.issue_field,
                            code=parsed.issue_code,
                            message=parsed.issue_message,
                        )
                    )
            self._session.flush()
            return self._load_batch(batch.id)

    def get_report(self, batch_id: int) -> CustomerImportBatch:
        batch = self._load_batch(batch_id)
        if batch is None:
            raise EntityNotFoundError("CustomerImportBatch", batch_id)
        return batch

    def commit(
        self,
        batch_id: int,
        *,
        command_id: UUID,
        expected_version: int,
        file_sha256: str,
        actor_user_id: int,
    ) -> ImportCommitProjection:
        with self._session.begin():
            acquire_advisory_locks(
                self._session, (("customer-import-batch", str(batch_id)),)
            )
            batch = self._session.scalar(
                select(CustomerImportBatch)
                .where(CustomerImportBatch.id == batch_id)
                .options(
                    selectinload(CustomerImportBatch.rows),
                    selectinload(CustomerImportBatch.results),
                )
                .with_for_update()
            )
            if batch is None:
                raise EntityNotFoundError("CustomerImportBatch", batch_id)
            if batch.status is CustomerImportStatus.COMMITTED:
                if (
                    batch.commit_command_id != command_id
                    or batch.version != expected_version
                    or batch.file_sha256 != file_sha256
                ):
                    raise IdempotencyConflictError(
                        "Customer import was committed by another command"
                    )
                return self._commit_projection(batch)
            if (
                batch.status is not CustomerImportStatus.VALID
                or batch.version != expected_version
                or batch.file_sha256 != file_sha256
            ):
                raise InvalidCustomerImportError(
                    "Customer import preview is invalid or stale"
                )
            identities = tuple(
                identity
                for row in batch.rows
                for identity in customer_identity_locks(row.email, row.phone_match_key)
            )
            acquire_advisory_locks(self._session, identities)
            committed_at = datetime.now(UTC)
            for row in batch.rows:
                customer = self._revalidate_and_apply(row)
                self._session.add(
                    CustomerImportResult(
                        batch=batch,
                        row_id=row.id,
                        customer_id=customer.id,
                        action=row.action,
                        committed_at=committed_at,
                    )
                )
            batch.status = CustomerImportStatus.COMMITTED
            batch.commit_command_id = command_id
            batch.committed_by_user_id = actor_user_id
            batch.committed_at = committed_at
            batch.updated_at = committed_at
            self._session.flush()
            return self._commit_projection(batch)

    def _parse(self, content: bytes) -> list[_ParsedRow]:
        if len(content) > MAX_IMPORT_BYTES:
            return [_file_error("CSV exceeds the configured size limit")]
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return [_file_error("CSV must be valid UTF-8")]
        try:
            records = list(csv.reader(StringIO(text), strict=True))
        except csv.Error:
            return [_file_error("CSV syntax is invalid")]
        if not records or tuple(records[0]) != CSV_HEADER:
            return [
                _file_error(
                    "CSV header must be name,company,email,phone,province", header=True
                )
            ]
        rows: list[_ParsedRow] = []
        for row_number, values in enumerate(records[1:], start=2):
            if not values or all(not value.strip() for value in values):
                continue
            if len(rows) >= MAX_IMPORT_ROWS:
                return [_file_error("CSV exceeds the configured row limit")]
            rows.append(self._parse_row(row_number, values))
        if not rows:
            return [_file_error("CSV contains no customer rows")]
        return rows

    def _parse_row(self, row_number: int, values: list[str]) -> _ParsedRow:
        if len(values) != len(CSV_HEADER):
            return _row_error(
                row_number,
                CustomerImportIssueCode.INVALID_ROW,
                None,
                "Row has an invalid column count",
            )
        if any(len(value) > MAX_FIELD_CHARS for value in values):
            return _row_error(
                row_number,
                CustomerImportIssueCode.INVALID_ROW,
                None,
                "Row contains an overlong field",
            )
        name = values[0].strip()
        company = normalize_optional_text(values[1])
        email = normalize_email(values[2])
        phone = normalize_optional_text(values[3])
        province = normalize_optional_text(values[4])
        profile = CustomerProfileInput(name, company, email, phone, province)
        parsed = _ParsedRow(row_number, profile, comparable_phone(phone))
        if not name:
            _set_issue(
                parsed,
                CustomerImportIssueCode.MISSING_NAME,
                "name",
                "Customer name is required",
            )
        elif email is not None:
            try:
                validate_email_format(email)
            except ValueError:
                _set_issue(
                    parsed,
                    CustomerImportIssueCode.INVALID_EMAIL,
                    "email",
                    "Email format is invalid",
                )
        if (
            parsed.issue_code is None
            and phone is not None
            and parsed.phone_match_key is None
        ):
            _set_issue(
                parsed,
                CustomerImportIssueCode.INVALID_PHONE,
                "phone",
                "Phone is too short for safe matching",
            )
        return parsed

    def _resolve_preview_rows(self, rows: list[_ParsedRow]) -> None:
        identity_counts: dict[tuple[str, str], int] = {}
        for row in rows:
            for identity in customer_identity_locks(
                row.profile.email, row.phone_match_key
            ):
                identity_counts[identity] = identity_counts.get(identity, 0) + 1
        resolver = CustomerIdentityResolver(self._session)
        for row in rows:
            if row.issue_code is not None:
                continue
            identities = customer_identity_locks(row.profile.email, row.phone_match_key)
            if any(identity_counts[identity] > 1 for identity in identities):
                _set_issue(
                    row,
                    CustomerImportIssueCode.DUPLICATE_IDENTITY,
                    None,
                    "Identity is repeated in this CSV",
                )
                continue
            resolution = resolver.resolve(
                normalized_email=row.profile.email,
                phone_match_key=row.phone_match_key,
                lock_rows=False,
            )
            if resolution.has_deleted_matches:
                _set_issue(
                    row,
                    CustomerImportIssueCode.DELETED_IDENTITY,
                    None,
                    "Identity matches a deleted customer",
                )
            elif resolution.is_ambiguous:
                _set_issue(
                    row,
                    CustomerImportIssueCode.AMBIGUOUS_IDENTITY,
                    None,
                    "Identity matches multiple customers",
                )
            elif resolution.customer is None:
                row.action = CustomerImportAction.CREATE
            else:
                row.resolved_customer_id = resolution.customer.id
                row.action = (
                    CustomerImportAction.ENRICH
                    if customer_would_be_enriched(resolution.customer, row.profile)
                    else CustomerImportAction.UNCHANGED
                )

    def _revalidate_and_apply(self, row: CustomerImportRow) -> Customer:
        profile = CustomerProfileInput(
            row.name, row.company, row.email, row.phone, row.province
        )
        resolution = CustomerIdentityResolver(self._session).resolve(
            normalized_email=row.email,
            phone_match_key=row.phone_match_key,
            lock_rows=True,
        )
        if resolution.has_deleted_matches or resolution.is_ambiguous:
            raise InvalidCustomerImportError("Customer identity changed after preview")
        if row.action is CustomerImportAction.CREATE:
            if resolution.customer is not None:
                raise InvalidCustomerImportError(
                    "Customer identity changed after preview"
                )
            return create_customer_from_profile(self._session, profile)
        customer = resolution.customer
        if customer is None or customer.id != row.resolved_customer_id:
            raise InvalidCustomerImportError("Customer identity changed after preview")
        would_enrich = customer_would_be_enriched(customer, profile)
        if (row.action is CustomerImportAction.ENRICH) != would_enrich:
            raise InvalidCustomerImportError("Customer changed after preview")
        if row.action is CustomerImportAction.ENRICH:
            enrich_customer_missing_fields(self._session, customer, profile)
        return customer

    def _load_batch(self, batch_id: int) -> CustomerImportBatch:
        batch = self._session.scalar(
            select(CustomerImportBatch)
            .where(CustomerImportBatch.id == batch_id)
            .options(
                selectinload(CustomerImportBatch.rows).selectinload(
                    CustomerImportRow.issues
                ),
                selectinload(CustomerImportBatch.results),
            )
        )
        if batch is None:
            raise EntityNotFoundError("CustomerImportBatch", batch_id)
        return batch

    @staticmethod
    def _commit_projection(batch: CustomerImportBatch) -> ImportCommitProjection:
        if batch.committed_at is None:
            raise InvalidCustomerImportError("Customer import has no commit timestamp")
        return ImportCommitProjection(
            batch_id=batch.id,
            status=batch.status,
            created_count=batch.create_count,
            enriched_count=batch.enrich_count,
            unchanged_count=batch.unchanged_count,
            customer_ids=tuple(sorted(result.customer_id for result in batch.results)),
            committed_at=batch.committed_at,
        )


def _file_error(message: str, *, header: bool = False) -> _ParsedRow:
    return _row_error(
        0,
        CustomerImportIssueCode.INVALID_HEADER
        if header
        else CustomerImportIssueCode.INVALID_FILE,
        None,
        message,
    )


def _row_error(
    row_number: int,
    code: CustomerImportIssueCode,
    field: str | None,
    message: str,
) -> _ParsedRow:
    row = _ParsedRow(
        row_number=row_number,
        profile=CustomerProfileInput("<invalid>", None, None, None, None),
        phone_match_key=None,
    )
    _set_issue(row, code, field, message)
    return row


def _set_issue(
    row: _ParsedRow,
    code: CustomerImportIssueCode,
    field: str | None,
    message: str,
) -> None:
    row.action = CustomerImportAction.ERROR
    row.issue_code = code
    row.issue_field = field
    row.issue_message = message
