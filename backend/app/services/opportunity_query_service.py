from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.sql.elements import ColumnElement

from app.models import (
    LeadSource,
    Opportunity,
    OpportunityProduct,
    OpportunityStatus,
)
from app.services.errors import EntityNotFoundError


class OpportunityQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_opportunities(
        self,
        *,
        page: int,
        page_size: int,
        status: OpportunityStatus | None,
        customer_id: int | None,
        assigned_user_id: int | None,
        source: LeadSource | None,
    ) -> tuple[list[Opportunity], int]:
        filters: list[ColumnElement[bool]] = [Opportunity.deleted_at.is_(None)]
        if status is not None:
            filters.append(Opportunity.status == status)
        if customer_id is not None:
            filters.append(Opportunity.customer_id == customer_id)
        if assigned_user_id is not None:
            filters.append(Opportunity.assigned_user_id == assigned_user_id)
        if source is not None:
            filters.append(Opportunity.source == source)

        total = self._session.scalar(
            select(func.count()).select_from(Opportunity).where(*filters)
        )
        statement = (
            select(Opportunity)
            .where(*filters)
            .options(*self._summary_load_options())
            .order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._session.scalars(statement)), total or 0

    def get_detail(self, opportunity_id: int) -> Opportunity:
        opportunity = self._session.scalar(
            select(Opportunity)
            .where(
                Opportunity.id == opportunity_id,
                Opportunity.deleted_at.is_(None),
            )
            .options(
                *self._summary_load_options(),
                selectinload(Opportunity.status_history),
            )
        )
        if opportunity is None:
            raise EntityNotFoundError("Opportunity", opportunity_id)
        return opportunity

    @staticmethod
    def _summary_load_options() -> tuple[ExecutableOption, ...]:
        return (
            joinedload(Opportunity.customer),
            joinedload(Opportunity.assigned_user),
            selectinload(Opportunity.opportunity_products).joinedload(
                OpportunityProduct.product
            ),
        )
