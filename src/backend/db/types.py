from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """A DateTime that's always UTC, both in the database and in Python —
    regardless of dialect.

    Plain DateTime(timezone=True) behaves differently across our two
    environments: SQLite (local dev) is timezone-agnostic in practice — it
    stores whatever it's given and returns naive datetimes on read — while
    Postgres's timestamptz (production) round-trips as timezone-aware UTC.
    Code that works locally can silently store the wrong instant in
    production, which is exactly what shifted appointment slot times by the
    browser's UTC offset there. This type normalizes both directions on
    every dialect, so the same code behaves identically everywhere.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return value
        if value.tzinfo is None:
            # Naive input is assumed to already be UTC — the API layer only
            # ever sends timezone-aware datetimes in (see schemas / frontend
            # ISO conversion); this is a defensive fallback, not the happy path.
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
