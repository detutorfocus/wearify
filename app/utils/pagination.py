"""
Reusable pagination utilities for all list endpoints.
"""
import math
from typing import TypeVar, Generic, Sequence
from pydantic import BaseModel
from fastapi import Query

T = TypeVar("T")


class PaginationParams:
    """FastAPI dependency for standard pagination query params."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        page_size: int = Query(20, ge=1, le=50, description="Items per page (max 50)"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PagedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope."""
    items: Sequence[T]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PaginationParams) -> "PagedResponse[T]":
        pages = math.ceil(total / params.page_size) if total > 0 else 1
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
            has_next=params.page < pages,
            has_prev=params.page > 1,
        )


def paginate_query(query, params: PaginationParams):
    """Apply offset/limit to a SQLAlchemy select query."""
    return query.offset(params.offset).limit(params.limit)
