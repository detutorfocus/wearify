# app/api/v1/endpoints/reviews.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


class ReviewCreate(BaseModel):
    product_id: UUID
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    body: str | None = None
    order_id: UUID | None = None


@router.get("/products/{product_id}")
async def get_product_reviews(
    product_id: UUID,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
):
    return await ReviewService(db).list_for_product(product_id, page, page_size)


@router.post("", status_code=201)
async def create_review(
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await ReviewService(db).create(
        product_id=data.product_id,
        customer_id=current_user.id,
        rating=data.rating,
        title=data.title,
        body=data.body,
        order_id=data.order_id,
    )
    await db.commit()
    return result


@router.post("/{review_id}/helpful")
async def mark_helpful(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = await ReviewService(db).mark_helpful(review_id)
    await db.commit()
    return {"helpful_count": count}


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await ReviewService(db).delete(review_id, current_user)
    await db.commit()
