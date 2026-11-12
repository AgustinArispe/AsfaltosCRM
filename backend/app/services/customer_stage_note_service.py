from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Opportunity, OpportunityStatusHistory, User
from app.services.customer_service import CustomerService


@dataclass(frozen=True, slots=True)
class CustomerStageNote:
    history: OpportunityStatusHistory
    author_name: str | None


class CustomerStageNoteService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_notes(
        self, customer_id: int, *, page: int, page_size: int
    ) -> tuple[list[CustomerStageNote], int]:
        CustomerService(self._session).get_customer(customer_id)
        filters = (
            Opportunity.customer_id == customer_id,
            OpportunityStatusHistory.note.is_not(None),
        )
        total = (
            self._session.scalar(
                select(func.count())
                .select_from(OpportunityStatusHistory)
                .join(
                    Opportunity,
                    Opportunity.id == OpportunityStatusHistory.opportunity_id,
                )
                .where(*filters)
            )
            or 0
        )
        rows = self._session.execute(
            select(OpportunityStatusHistory, User.full_name)
            .join(
                Opportunity, Opportunity.id == OpportunityStatusHistory.opportunity_id
            )
            .outerjoin(User, User.id == OpportunityStatusHistory.changed_by_user_id)
            .where(*filters)
            .order_by(
                OpportunityStatusHistory.changed_at.desc(),
                OpportunityStatusHistory.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).tuples()
        return [
            CustomerStageNote(history, author_name) for history, author_name in rows
        ], total
