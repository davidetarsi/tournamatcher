from __future__ import annotations
from datetime import datetime, timezone
from services.tournament_service import get_effective_deadline


def test_explicit_deadline_with_z_suffix():
    schema = {"edit_deadline": "2026-07-14T21:59:00.000Z"}
    result = get_effective_deadline(schema)
    assert result == datetime(2026, 7, 14, 21, 59, 0, tzinfo=timezone.utc)


def test_explicit_deadline_with_utc_offset():
    schema = {"edit_deadline": "2026-07-14T21:59:00+00:00"}
    result = get_effective_deadline(schema)
    assert result == datetime(2026, 7, 14, 21, 59, 0, tzinfo=timezone.utc)


def test_start_date_fallback_computes_prev_day_2359():
    schema = {"start_date": "2026-07-15"}
    result = get_effective_deadline(schema)
    assert result == datetime(2026, 7, 14, 23, 59, 0, tzinfo=timezone.utc)


def test_both_null_returns_none():
    result = get_effective_deadline({})
    assert result is None


def test_explicit_deadline_overrides_start_date():
    schema = {"edit_deadline": "2026-06-01T10:00:00Z", "start_date": "2026-07-15"}
    result = get_effective_deadline(schema)
    assert result == datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
