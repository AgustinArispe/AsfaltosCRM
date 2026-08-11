from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import DatabaseSession, SupervisorUser
from app.schemas import (
    CustomerImportCommitRequest,
    CustomerImportCommitResponse,
    CustomerImportReportResponse,
)
from app.services.customer_import_service import MAX_IMPORT_BYTES, CustomerImportService

router = APIRouter(prefix="/customer-imports", tags=["customer imports"])


@router.post(
    "/dry-run",
    response_model=CustomerImportReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def dry_run_customer_import(
    session: DatabaseSession,
    supervisor: SupervisorUser,
    client_import_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
) -> CustomerImportReportResponse:
    content = file.file.read(MAX_IMPORT_BYTES + 1)
    batch = CustomerImportService(session).dry_run(
        client_import_id=client_import_id,
        filename=file.filename or "customers.csv",
        content=content,
        actor_user_id=supervisor.id,
    )
    return CustomerImportReportResponse.model_validate(batch, from_attributes=True)


@router.get("/{batch_id}", response_model=CustomerImportReportResponse)
def get_customer_import(
    batch_id: int,
    session: DatabaseSession,
    _supervisor: SupervisorUser,
) -> CustomerImportReportResponse:
    batch = CustomerImportService(session).get_report(batch_id)
    return CustomerImportReportResponse.model_validate(batch, from_attributes=True)


@router.post("/{batch_id}/commit", response_model=CustomerImportCommitResponse)
def commit_customer_import(
    batch_id: int,
    payload: CustomerImportCommitRequest,
    session: DatabaseSession,
    supervisor: SupervisorUser,
) -> CustomerImportCommitResponse:
    result = CustomerImportService(session).commit(
        batch_id,
        command_id=payload.command_id,
        expected_version=payload.expected_version,
        file_sha256=payload.file_sha256,
        actor_user_id=supervisor.id,
    )
    return CustomerImportCommitResponse.model_validate(result, from_attributes=True)
