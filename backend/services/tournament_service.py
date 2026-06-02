from __future__ import annotations
from datetime import datetime, timedelta, timezone


def get_effective_deadline(schema: dict) -> datetime | None:
    """
    Calcola la deadline rigorosamente in UTC.
    Presuppone che il frontend invii stringhe ISO-8601 con suffisso Z (UTC).
    """
    if ed := schema.get("edit_deadline"):
        dt = datetime.fromisoformat(ed.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    if sd := schema.get("start_date"):
        dt = datetime.fromisoformat(sd).replace(tzinfo=timezone.utc)
        return dt - timedelta(minutes=1)
    return None
