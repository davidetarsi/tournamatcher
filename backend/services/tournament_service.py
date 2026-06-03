from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone


def generate_slug(name: str, start_date: str | None) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    if start_date:
        date_part = re.sub(r"[^a-z0-9]+", "-", start_date.lower()).strip("-")
        base = f"{base}-{date_part}"
    return base


def reserve_slug_in_transaction(
    transaction,
    slugs_ref,
    base_slug: str,
    tournament_id: str,
    t_ref,
    doc_data: dict,
) -> str:
    """Called within a Firestore transaction. Finds free slug and writes both docs."""
    candidate = base_slug
    i = 2
    while transaction.get(slugs_ref.document(candidate)).exists:
        candidate = f"{base_slug}-{i}"
        i += 1
    transaction.set(slugs_ref.document(candidate), {"tournament_id": tournament_id})
    transaction.set(t_ref, {**doc_data, "slug": candidate})
    return candidate


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
