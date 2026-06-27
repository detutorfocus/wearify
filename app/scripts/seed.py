"""
Wearify Database Seeder
=======================
Run with:  docker-compose exec backend python -m app.scripts.seed
Or:        python -m app.scripts.seed
"""
import asyncio
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, create_tables
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.vendor import Vendor, KYCStatus, SubscriptionPlan
from app.models.category import Category
from app.models.product import Product, ProductImage, ProductVariant, ProductStatus
from app.models.wallet import Wallet


# ── Seed data ─────────────────────────────────────────────────────────────────

CATEGORIES = [
    {"name": "Women",       "slug": "women",       "icon_url": None},
    {"name": "Men",         "slug": "men",         "icon_url": None},
    {"name": "Accessories", "slug": "accessories", "icon_url": None},
    {"name": "Shoes",       "slug": "shoes",       "icon_url": None},
    {"name": "Bags",        "slug": "bags",        "icon_url": None},
    {"name": "Kids",        "slug": "kids",        "icon_url": None},
]

USERS = [
    {
        "email": "admin@wearify.com",
        "password": "Admin1234!",
        "full_name": "Wearify Admin",
        "role": UserRole.admin,
        "is_verified": True,
    },
    {
        "email": "vendor@wearify.com",
        "password": "Vendor1234!",
        "full_name": "Lagos Threads",
        "role": UserRole.vendor,
        "is_verified": True,
    },
    {
        "email": "customer@wearify.com",
        "password": "Customer1234!",
        "full_name": "Jane Doe",
        "role": UserRole.customer,
        "is_verified": True,
    },
]

VENDOR_DATA = {
    "store_name": "Lagos Threads",
    "store_slug": "lagos-threads",
    "description": "Premium Nigerian fashion — Ankara prints, agbada, and contemporary fusion wear.",
    "kyc_status": KYCStatus.approved,
    "subscription_plan": SubscriptionPlan.professional,
    "commission_rate": Decimal("10.0"),
    "is_featured": True,
    "rating": Decimal("4.8"),
    "total_sales": 312,
}

PRODUCTS = [
    {
        "name": "Ankara Wrap Midi Dress",
        "description": "Hand-crafted Ankara fabric wrap dress with bold geometric patterns. Perfect for events, office, or casual outings.",
        "base_price": Decimal("18500"),
        "sale_price": Decimal("14900"),
        "is_on_sale": True,
        "sku": "LGT-AWM-001",
        "stock_quantity": 24,
        "status": ProductStatus.active,
        "is_featured": True,
        "tags": ["ankara", "dress", "women", "african-print"],
        "meta_title": "Ankara Wrap Midi Dress — Lagos Threads",
        "meta_description": "Beautiful hand-crafted Ankara wrap dress. Shop African fashion at Wearify.",
        "variants": [
            {"size": "XS", "color": "Blue/Orange", "color_hex": "#1E4D8C", "stock_quantity": 4, "additional_price": Decimal("0")},
            {"size": "S",  "color": "Blue/Orange", "color_hex": "#1E4D8C", "stock_quantity": 6, "additional_price": Decimal("0")},
            {"size": "M",  "color": "Blue/Orange", "color_hex": "#1E4D8C", "stock_quantity": 8, "additional_price": Decimal("0")},
            {"size": "L",  "color": "Blue/Orange", "color_hex": "#1E4D8C", "stock_quantity": 4, "additional_price": Decimal("0")},
            {"size": "XL", "color": "Blue/Orange", "color_hex": "#1E4D8C", "stock_quantity": 2, "additional_price": Decimal("500")},
        ],
    },
    {
        "name": "Men's Embroidered Agbada Set",
        "description": "Three-piece agbada set with intricate hand embroidery. Includes buba, sokoto, and agbada. Available in white, navy, and burgundy.",
        "base_price": Decimal("65000"),
        "sale_price": None,
        "is_on_sale": False,
        "sku": "LGT-MEA-002",
        "stock_quantity": 15,
        "status": ProductStatus.active,
        "is_featured": True,
        "tags": ["agbada", "men", "traditional", "embroidered"],
        "meta_title": "Men's Embroidered Agbada Set — Lagos Threads",
        "meta_description": "Premium 3-piece agbada set with hand embroidery. Nigerian traditional wear.",
        "variants": [
            {"size": "M",    "color": "White",    "color_hex": "#F5F5F5", "stock_quantity": 5, "additional_price": Decimal("0")},
            {"size": "L",    "color": "White",    "color_hex": "#F5F5F5", "stock_quantity": 4, "additional_price": Decimal("0")},
            {"size": "XL",   "color": "Navy",     "color_hex": "#1B2A4A", "stock_quantity": 3, "additional_price": Decimal("0")},
            {"size": "2XL",  "color": "Burgundy", "color_hex": "#6D1A1A", "stock_quantity": 3, "additional_price": Decimal("2000")},
        ],
    },
    {
        "name": "Beaded Clutch Bag",
        "description": "Hand-beaded evening clutch with Yoruba-inspired patterns. Each piece is unique.",
        "base_price": Decimal("12000"),
        "sale_price": None,
        "is_on_sale": False,
        "sku": "LGT-BCB-003",
        "stock_quantity": 8,
        "status": ProductStatus.active,
        "is_featured": False,
        "tags": ["bag", "clutch", "beaded", "accessories", "evening"],
        "meta_title": "Beaded Clutch Bag — Lagos Threads",
        "meta_description": "Handmade beaded clutch with Yoruba-inspired patterns.",
        "variants": [
            {"size": None, "color": "Gold",   "color_hex": "#C9A84C", "stock_quantity": 4, "additional_price": Decimal("0")},
            {"size": None, "color": "Silver", "color_hex": "#A8A8A8", "stock_quantity": 4, "additional_price": Decimal("0")},
        ],
    },
    {
        "name": "Lace Iro and Buba Set",
        "description": "Elegant French lace iro and buba set. Fully lined with matching gele fabric included.",
        "base_price": Decimal("42000"),
        "sale_price": Decimal("35000"),
        "is_on_sale": True,
        "sku": "LGT-LIB-004",
        "stock_quantity": 10,
        "status": ProductStatus.active,
        "is_featured": True,
        "tags": ["lace", "iro", "buba", "women", "traditional"],
        "meta_title": "Lace Iro and Buba Set — Lagos Threads",
        "meta_description": "Premium French lace iro and buba. Complete set with gele.",
        "variants": [
            {"size": "S",  "color": "Champagne", "color_hex": "#F7E7CE", "stock_quantity": 3, "additional_price": Decimal("0")},
            {"size": "M",  "color": "Champagne", "color_hex": "#F7E7CE", "stock_quantity": 4, "additional_price": Decimal("0")},
            {"size": "L",  "color": "Dusty Rose","color_hex": "#DCAE96", "stock_quantity": 3, "additional_price": Decimal("0")},
        ],
    },
    {
        "name": "Contemporary Fusion Blazer",
        "description": "Modern blazer with African print lining. Tailored fit, premium cotton-blend exterior.",
        "base_price": Decimal("28000"),
        "sale_price": None,
        "is_on_sale": False,
        "sku": "LGT-CFB-005",
        "stock_quantity": 18,
        "status": ProductStatus.active,
        "is_featured": False,
        "tags": ["blazer", "men", "contemporary", "fusion", "office"],
        "meta_title": "Contemporary Fusion Blazer — Lagos Threads",
        "meta_description": "Modern tailored blazer with African print lining.",
        "variants": [
            {"size": "S",   "color": "Black", "color_hex": "#1A1A1A", "stock_quantity": 4, "additional_price": Decimal("0")},
            {"size": "M",   "color": "Black", "color_hex": "#1A1A1A", "stock_quantity": 6, "additional_price": Decimal("0")},
            {"size": "L",   "color": "Black", "color_hex": "#1A1A1A", "stock_quantity": 5, "additional_price": Decimal("0")},
            {"size": "XL",  "color": "Navy",  "color_hex": "#1B2A4A", "stock_quantity": 3, "additional_price": Decimal("0")},
        ],
    },
    {
        "name": "Adire Tie-Dye Shorts",
        "description": "Handmade adire (tie-dye) shorts using traditional indigo dyeing techniques from Abeokuta.",
        "base_price": Decimal("8500"),
        "sale_price": None,
        "is_on_sale": False,
        "sku": "LGT-ADS-006",
        "stock_quantity": 30,
        "status": ProductStatus.active,
        "is_featured": False,
        "tags": ["adire", "shorts", "tie-dye", "unisex", "casual"],
        "meta_title": "Adire Tie-Dye Shorts",
        "meta_description": "Traditional adire tie-dye shorts handmade in Abeokuta.",
        "variants": [
            {"size": "S",  "color": "Indigo", "color_hex": "#3F51B5", "stock_quantity": 8,  "additional_price": Decimal("0")},
            {"size": "M",  "color": "Indigo", "color_hex": "#3F51B5", "stock_quantity": 10, "additional_price": Decimal("0")},
            {"size": "L",  "color": "Indigo", "color_hex": "#3F51B5", "stock_quantity": 8,  "additional_price": Decimal("0")},
            {"size": "XL", "color": "Indigo", "color_hex": "#3F51B5", "stock_quantity": 4,  "additional_price": Decimal("0")},
        ],
    },
]


# ── Seeder logic ───────────────────────────────────────────────────────────────

async def seed(db: AsyncSession) -> None:
    print("🌱 Starting Wearify database seed...")

    # 1. Categories
    print("  → Seeding categories...")
    category_map: dict[str, Category] = {}
    for cat_data in CATEGORIES:
        cat = Category(
            id=uuid.uuid4(),
            name=cat_data["name"],
            slug=cat_data["slug"],
            is_active=True,
            sort_order=CATEGORIES.index(cat_data),
        )
        db.add(cat)
        category_map[cat_data["slug"]] = cat
    await db.flush()
    print(f"     ✓ {len(CATEGORIES)} categories created")

    # 2. Users
    print("  → Seeding users...")
    user_map: dict[str, User] = {}
    for u_data in USERS:
        user = User(
            id=uuid.uuid4(),
            email=u_data["email"],
            hashed_password=get_password_hash(u_data["password"]),
            full_name=u_data["full_name"],
            role=u_data["role"],
            is_active=True,
            is_verified=u_data["is_verified"],
        )
        db.add(user)
        user_map[u_data["email"]] = user
    await db.flush()
    print(f"     ✓ {len(USERS)} users created")
    for u_data in USERS:
        print(f"       Email: {u_data['email']}  Password: {u_data['password']}")

    # 3. Vendor
    print("  → Seeding vendor...")
    vendor_user = user_map["vendor@wearify.com"]
    vendor = Vendor(
        id=uuid.uuid4(),
        user_id=vendor_user.id,
        **{k: v for k, v in VENDOR_DATA.items()},
    )
    db.add(vendor)
    await db.flush()

    # Wallet for vendor
    wallet = Wallet(
        id=uuid.uuid4(),
        vendor_id=vendor.id,
        balance=Decimal("125000"),
        pending_balance=Decimal("18500"),
        total_earned=Decimal("143500"),
        total_withdrawn=Decimal("0"),
    )
    db.add(wallet)
    await db.flush()
    print("     ✓ Vendor 'Lagos Threads' created with wallet")

    # 4. Products
    print("  → Seeding products...")
    for p_data in PRODUCTS:
        variants_data = p_data.pop("variants", [])

        # Assign category based on tags
        category_id = None
        if "women" in p_data.get("tags", []) or "dress" in p_data.get("tags", []):
            category_id = category_map["women"].id
        elif "men" in p_data.get("tags", []):
            category_id = category_map["men"].id
        elif any(t in p_data.get("tags", []) for t in ["bag", "clutch", "accessories"]):
            category_id = category_map["accessories"].id

        product = Product(
            id=uuid.uuid4(),
            vendor_id=vendor.id,
            category_id=category_id,
            **p_data,
        )
        db.add(product)
        await db.flush()

        # Product image placeholder (Cloudinary would have real URLs)
        img = ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            url=f"https://via.placeholder.com/800x1067/1A1A28/C9A84C?text={product.name.replace(' ', '+')}",
            alt_text=product.name,
            sort_order=0,
            is_primary=True,
        )
        db.add(img)

        # Variants
        for v_data in variants_data:
            variant = ProductVariant(
                id=uuid.uuid4(),
                product_id=product.id,
                size=v_data["size"],
                color=v_data["color"],
                color_hex=v_data["color_hex"],
                stock_quantity=v_data["stock_quantity"],
                additional_price=v_data["additional_price"],
                sku_variant=f"{product.sku}-{v_data['size'] or 'OS'}-{v_data['color'][:3].upper()}",
            )
            db.add(variant)

        print(f"     ✓ {product.name} ({len(variants_data)} variants)")

    await db.commit()
    print("\n✅ Seed complete!")
    print("=" * 50)
    print("Login credentials:")
    for u in USERS:
        print(f"  {u['role'].value:10s}  {u['email']:30s}  {u['password']}")
    print("=" * 50)


async def main() -> None:
    print("Creating tables if not exist...")
    await create_tables()
    async with AsyncSessionLocal() as db:
        try:
            await seed(db)
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Seed failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
