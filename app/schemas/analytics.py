"""
Pydantic schemas for analytics endpoints.
Used by vendor dashboard and admin analytics APIs.
"""
from pydantic import BaseModel
from datetime import date
from typing import Optional


class DailyRevenue(BaseModel):
    date: str
    revenue: float
    orders: int


class TopProduct(BaseModel):
    product_id: str
    product_name: str
    units_sold: int
    revenue: float
    slug: str


class VendorAnalyticsResponse(BaseModel):
    period_days: int
    total_revenue: float
    total_orders: int
    avg_order_value: float
    total_units_sold: int
    revenue_change_pct: float   # vs previous period
    orders_change_pct: float
    daily_revenue: list[DailyRevenue]
    top_products: list[TopProduct]
    top_categories: list[dict]


class AdminAnalyticsResponse(BaseModel):
    period_days: int
    total_revenue: float
    total_orders: int
    new_users: int
    new_vendors: int
    avg_order_value: float
    gmv: float                  # gross merchandise value
    platform_commission: float
    revenue_change_pct: float
    daily_revenue: list[DailyRevenue]
    top_vendors: list[dict]
    order_status_breakdown: dict
    payment_provider_breakdown: dict


class RevenueByPeriod(BaseModel):
    period: str
    revenue: float
    orders: int
    new_customers: int


class ConversionFunnel(BaseModel):
    visitors: int
    product_views: int
    add_to_cart: int
    checkout_started: int
    orders_placed: int
    conversion_rate: float
