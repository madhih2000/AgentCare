from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slots_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end
