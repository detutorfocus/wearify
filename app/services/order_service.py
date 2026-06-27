import math
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.order import Order, OrderItem, OrderStatus
from app.models.cart import CartItem
from app.models.product import Product, ProductVariant
from app.models.vendor import Vendor
from app.schemas.order import OrderCreate


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_from_cart(self, customer_id: UUID, order_data: OrderCreate) -> dict:
        # Fetch cart items
        from sqlalchemy.orm import selectinload as _sil
        result = await self.db.execute(
            select(CartItem)
            .options(
                _sil(CartItem.product),
                _sil(CartItem.variant),
            )
            .where(CartItem.customer_id == customer_id)
        )
        cart_items = result.scalars().all()

        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Validate stock and build order items
        order_items = []
        subtotal = 0.0

        for item in cart_items:
            product = item.product
            if not product or product.status != "active":
                raise HTTPException(status_code=400, detail=f"Product {product.name} is no longer available")

            stock = item.variant.stock_quantity if item.variant else product.stock_quantity
            if stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name}. Available: {stock}"
                )

            unit_price = float(product.sale_price or product.base_price)
            if item.variant:
                unit_price += float(item.variant.additional_price)

            item_subtotal = unit_price * item.quantity

            # Get vendor commission rate
            vendor_result = await self.db.execute(select(Vendor).where(Vendor.id == product.vendor_id))
            vendor = vendor_result.scalar_one()
            commission = item_subtotal * (float(vendor.commission_rate) / 100)
            earnings = item_subtotal - commission

            order_items.append({
                "product": product,
                "variant": item.variant,
                "vendor_id": product.vendor_id,
                "quantity": item.quantity,
                "unit_price": unit_price,
                "subtotal": item_subtotal,
                "vendor_commission": commission,
                "vendor_earnings": earnings,
            })
            subtotal += item_subtotal

        # Deduct stock (reserve)
        for item_data in order_items:
            if item_data["variant"]:
                item_data["variant"].stock_quantity -= item_data["quantity"]
            else:
                item_data["product"].stock_quantity -= item_data["quantity"]

        total = subtotal  # add shipping logic here if needed

        # Create order
        order = Order(
            customer_id=customer_id,
            status=OrderStatus.pending,
            subtotal=subtotal,
            shipping_fee=0.0,
            discount=0.0,
            total=total,
            shipping_address=order_data.shipping_address.model_dump(),
            payment_method=order_data.payment_method,
            payment_status="pending",
            notes=order_data.notes,
        )
        self.db.add(order)
        await self.db.flush()

        # Create order items
        for item_data in order_items:
            oi = OrderItem(
                order_id=order.id,
                product_id=item_data["product"].id,
                vendor_id=item_data["vendor_id"],
                variant_id=item_data["variant"].id if item_data["variant"] else None,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                subtotal=item_data["subtotal"],
                vendor_commission=item_data["vendor_commission"],
                vendor_earnings=item_data["vendor_earnings"],
            )
            self.db.add(oi)

        # Clear cart
        for cart_item in cart_items:
            await self.db.delete(cart_item)

        await self.db.flush()
        # Re-fetch with eager-loaded items to avoid lazy-load in _serialize
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order.id)
        )
        order = result.scalar_one()
        return self._serialize(order)

    async def get_by_id(self, order_id: UUID) -> dict | None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        return self._serialize(order) if order else None

    async def list_customer_orders(
        self, customer_id: UUID, page: int = 1, page_size: int = 10, status_filter: str = None
    ) -> dict:
        query = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == customer_id)
        )
        if status_filter:
            query = query.where(Order.status == status_filter)
        query = query.order_by(Order.created_at.desc())

        from sqlalchemy import func
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        offset = (page - 1) * page_size
        result = await self.db.execute(query.offset(offset).limit(page_size))
        orders = result.scalars().all()

        return {
            "items": [self._serialize(o) for o in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def cancel_order(self, order_id: UUID, requesting_user) -> dict:
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if str(order.customer_id) != str(requesting_user.id) and requesting_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        if order.status not in (OrderStatus.pending, OrderStatus.confirmed):
            raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")

        order.status = OrderStatus.cancelled

        # Restore stock
        for item in order.items:
            product_result = await self.db.execute(select(Product).where(Product.id == item.product_id))
            product = product_result.scalar_one_or_none()
            if product:
                product.stock_quantity += item.quantity

        await self.db.flush()
        # Re-fetch with eager-loaded items to avoid lazy-load in _serialize
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order.id)
        )
        order = result.scalar_one()
        return self._serialize(order)

    async def update_status(
        self, order_id: UUID, new_status: str, tracking_number: str, requesting_user
    ) -> dict:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order.status = new_status
        if tracking_number:
            order.tracking_number = tracking_number

        # When delivered, send notification task
        if new_status == "delivered":
            from app.tasks.notification_tasks import notify_order_delivered
            notify_order_delivered.delay(str(order_id), str(order.customer_id))

        await self.db.flush()
        # Re-fetch with eager-loaded items to avoid lazy-load in _serialize
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order.id)
        )
        order = result.scalar_one()
        return self._serialize(order)

    def _serialize(self, order: Order) -> dict:
        return {
            "id": str(order.id),
            "customer_id": str(order.customer_id),
            "status": order.status,
            "subtotal": float(order.subtotal),
            "shipping_fee": float(order.shipping_fee),
            "discount": float(order.discount),
            "total": float(order.total),
            "shipping_address": order.shipping_address,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "tracking_number": order.tracking_number,
            "items": [
                {
                    "id": str(i.id),
                    "product_id": str(i.product_id),
                    "vendor_id": str(i.vendor_id),
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                    "subtotal": float(i.subtotal),
                }
                for i in (order.items or [])
            ],
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
