"""
Review service — create, list, moderate, mark helpful.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models.review import Review


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_product(
        self, product_id: UUID, page: int = 1, page_size: int = 10
    ) -> dict:
        query = (
            select(Review)
            .where(Review.product_id == product_id, Review.is_approved == True)
            .order_by(Review.created_at.desc())
        )
        count = (await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )).scalar()
        avg = (await self.db.execute(
            select(func.avg(Review.rating)).where(Review.product_id == product_id)
        )).scalar()

        offset = (page - 1) * page_size
        result = await self.db.execute(query.offset(offset).limit(page_size))
        reviews = result.scalars().all()

        return {
            "items": [self._serialize(r) for r in reviews],
            "total": count,
            "avg_rating": round(float(avg or 0), 1),
            "page": page,
            "page_size": page_size,
        }

    async def create(
        self,
        product_id: UUID,
        customer_id: UUID,
        rating: int,
        title: str | None,
        body: str | None,
        order_id: UUID | None,
    ) -> dict:
        # One review per customer per product
        existing = (await self.db.execute(
            select(Review).where(
                Review.product_id == product_id,
                Review.customer_id == customer_id,
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="You already reviewed this product")

        if not 1 <= rating <= 5:
            raise HTTPException(status_code=422, detail="Rating must be between 1 and 5")

        review = Review(
            product_id=product_id,
            customer_id=customer_id,
            order_id=order_id,
            rating=rating,
            title=title,
            body=body,
            is_verified_purchase=order_id is not None,
        )
        self.db.add(review)
        await self.db.flush()

        # Update product aggregate rating
        await self._update_product_rating(product_id)
        return self._serialize(review)

    async def mark_helpful(self, review_id: UUID) -> int:
        result = await self.db.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        review.helpful_count += 1
        await self.db.flush()
        return review.helpful_count

    async def delete(self, review_id: UUID, requesting_user) -> None:
        result = await self.db.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        if str(review.customer_id) != str(requesting_user.id) and requesting_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        product_id = review.product_id
        await self.db.delete(review)
        await self.db.flush()
        await self._update_product_rating(product_id)

    async def _update_product_rating(self, product_id: UUID) -> None:
        from app.models.product import Product
        from sqlalchemy import update
        avg = (await self.db.execute(
            select(func.avg(Review.rating))
            .where(Review.product_id == product_id, Review.is_approved == True)
        )).scalar() or 0
        await self.db.execute(
            update(Product).where(Product.id == product_id).values(rating_avg=round(float(avg), 2))
        )

    def _serialize(self, r: Review) -> dict:
        return {
            "id": str(r.id),
            "product_id": str(r.product_id),
            "customer_id": str(r.customer_id),
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "is_verified_purchase": r.is_verified_purchase,
            "helpful_count": r.helpful_count,
            "is_approved": r.is_approved,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
