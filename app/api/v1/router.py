from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, products, vendors, orders,
    payments, reviews, cart, wishlist,
    notifications, admin,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(vendors.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(reviews.router)
api_router.include_router(cart.router)
api_router.include_router(wishlist.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
