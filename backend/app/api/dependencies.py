from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def get_db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@dataclass(frozen=True, slots=True)
class PaginationParams:
    page: int
    page_size: int


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    ] = DEFAULT_PAGE_SIZE,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


DatabaseSession = Annotated[Session, Depends(get_db_session)]
Pagination = Annotated[PaginationParams, Depends(get_pagination)]
