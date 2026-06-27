"""
Clear all Redis caches for Wearify.

Usage:
  docker-compose exec backend python -m app.scripts.clear_cache
  docker-compose exec backend python -m app.scripts.clear_cache --pattern "products:*"
"""
import asyncio
import argparse
from app.core.redis import redis_client


async def clear(pattern: str = "*") -> None:
    keys = await redis_client.keys(pattern)
    if not keys:
        print(f"No keys found matching: {pattern}")
        return
    await redis_client.delete(*keys)
    print(f"✅ Cleared {len(keys)} keys matching: {pattern}")
    await redis_client.aclose()


def main():
    parser = argparse.ArgumentParser(description="Clear Wearify Redis cache")
    parser.add_argument("--pattern", default="*", help="Key pattern to clear (default: all)")
    args = parser.parse_args()
    asyncio.run(clear(args.pattern))


if __name__ == "__main__":
    main()
