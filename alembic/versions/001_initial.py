"""Initial schema - all tables

Revision ID: 001_initial
Create Date: 2025-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("role", sa.Enum("customer", "vendor", "admin", name="userrole"), nullable=False, server_default="customer"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_verified", sa.Boolean(), server_default="false"),
        sa.Column("google_id", sa.String(255), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    # ── Categories ────────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(150), unique=True, nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("icon_url", sa.String(500), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])

    # ── Vendors ───────────────────────────────────────────────────────────────
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("store_name", sa.String(255), unique=True, nullable=False),
        sa.Column("store_slug", sa.String(300), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("banner_url", sa.String(500), nullable=True),
        sa.Column("kyc_status", sa.Enum("pending", "approved", "rejected", name="kycstatus"), server_default="pending"),
        sa.Column("kyc_documents", postgresql.JSONB(), server_default="{}"),
        sa.Column("commission_rate", sa.Numeric(5, 2), server_default="10.0"),
        sa.Column("subscription_plan", sa.Enum("free", "starter", "professional", "enterprise", name="subscriptionplan"), server_default="free"),
        sa.Column("is_featured", sa.Boolean(), server_default="false"),
        sa.Column("rating", sa.Numeric(3, 2), server_default="0.0"),
        sa.Column("total_sales", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vendors_store_slug", "vendors", ["store_slug"])
    op.create_index("ix_vendors_kyc_status", "vendors", ["kyc_status"])

    # ── Products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(300), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_on_sale", sa.Boolean(), server_default="false"),
        sa.Column("flash_sale_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sku", sa.String(100), unique=True, nullable=False),
        sa.Column("stock_quantity", sa.Integer(), server_default="0"),
        sa.Column("status", sa.Enum("draft", "active", "archived", name="productstatus"), server_default="draft"),
        sa.Column("is_featured", sa.Boolean(), server_default="false"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("view_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_products_slug", "products", ["slug"])
    op.create_index("ix_products_vendor_id", "products", ["vendor_id"])
    op.create_index("ix_products_status", "products", ["status"])
    op.create_index("ix_products_is_featured", "products", ["is_featured"])
    # GIN index for tags array (fast tag filtering)
    op.execute("CREATE INDEX ix_products_tags_gin ON products USING GIN (tags)")
    # Composite index for vendor + status (vendor dashboard query)
    op.create_index("ix_products_vendor_status", "products", ["vendor_id", "status"])

    # ── Product Images ────────────────────────────────────────────────────────
    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("alt_text", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Product Variants ──────────────────────────────────────────────────────
    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("size", sa.String(20), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("color_hex", sa.String(7), nullable=True),
        sa.Column("stock_quantity", sa.Integer(), server_default="0"),
        sa.Column("additional_price", sa.Numeric(10, 2), server_default="0"),
        sa.Column("sku_variant", sa.String(150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Orders ────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Enum("pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded", name="orderstatus"), server_default="pending"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_fee", sa.Numeric(10, 2), server_default="0"),
        sa.Column("discount", sa.Numeric(10, 2), server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_address", postgresql.JSONB(), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("payment_status", sa.String(50), server_default="pending"),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    # Partial index for pending orders (most queried status)
    op.execute("CREATE INDEX ix_orders_pending ON orders (created_at) WHERE status = 'pending'")

    # ── Wallets ───────────────────────────────────────────────────────────────
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False, unique=True),
        sa.Column("balance", sa.Numeric(14, 2), server_default="0"),
        sa.Column("pending_balance", sa.Numeric(14, 2), server_default="0"),
        sa.Column("total_earned", sa.Numeric(14, 2), server_default="0"),
        sa.Column("total_withdrawn", sa.Numeric(14, 2), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Audit Log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_created_at", "audit_logs", ["created_at"])
    # Partition audit_logs by month in production for performance
    # op.execute("... PARTITION BY RANGE (created_at)")


def downgrade() -> None:
    tables = [
        "audit_logs", "wallets", "orders", "product_variants",
        "product_images", "products", "vendors", "categories", "users"
    ]
    for table in tables:
        op.drop_table(table)

    # Drop enums
    for enum in ["userrole", "kycstatus", "subscriptionplan", "productstatus", "orderstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
