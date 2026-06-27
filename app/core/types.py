"""
Database type compatibility layer.

Provides types that work transparently on both PostgreSQL (production)
and SQLite (testing) without requiring separate test configurations.
"""
import os
import uuid
from sqlalchemy import String, JSON, Text
from sqlalchemy import types as sa_types
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

_db_url = os.getenv("DATABASE_URL", "postgresql")
_is_postgres = "postgresql" in _db_url or "postgres" in _db_url


class CompatUUID(sa_types.TypeDecorator):
    """
    UUID column that stores as native UUID on PostgreSQL and as VARCHAR(36)
    on SQLite. Accepts both uuid.UUID objects and UUID strings as input.
    """
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            if dialect.name == "postgresql":
                return value
            return str(value)
        # String input
        try:
            parsed = uuid.UUID(str(value))
            return str(parsed) if dialect.name != "postgresql" else parsed
        except (ValueError, AttributeError):
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError):
            return value


class CompatJSON(sa_types.TypeDecorator):
    """JSONB on PostgreSQL, JSON on SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


class CompatArray(sa_types.TypeDecorator):
    """ARRAY(Text) on PostgreSQL, Text (JSON-serialized) on SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY
            return dialect.type_descriptor(ARRAY(Text()))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is None:
            return "[]"
        import json
        return json.dumps(value) if isinstance(value, list) else value

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value or []
        if value is None:
            return []
        import json
        try:
            result = json.loads(value)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
