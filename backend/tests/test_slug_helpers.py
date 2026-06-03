from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from services.tournament_service import generate_slug, reserve_slug_in_transaction


def test_generate_slug_with_date():
    assert generate_slug("Torneo Estivo", "2026-07-15") == "torneo-estivo-2026-07-15"


def test_generate_slug_without_date():
    assert generate_slug("Torneo Estivo", None) == "torneo-estivo"


def test_generate_slug_special_chars():
    assert generate_slug("Torneo d'Estate!", None) == "torneo-d-estate"


def test_generate_slug_multiple_spaces():
    assert generate_slug("  Torneo  Calcetto  ", None) == "torneo-calcetto"


def test_generate_slug_numbers():
    assert generate_slug("Torneo 2026", "2026-07-15") == "torneo-2026-2026-07-15"


def test_reserve_slug_no_collision():
    """When slug does not exist, uses base slug."""
    transaction = MagicMock()
    snap = MagicMock()
    snap.exists = False
    transaction.get.return_value = snap

    slugs_ref = MagicMock()
    t_ref = MagicMock()
    doc_data = {"name": "Torneo", "admin_uid": "uid-123", "status": "draft"}

    result = reserve_slug_in_transaction(transaction, slugs_ref, "torneo-estivo", "uuid-1", t_ref, doc_data)

    assert result == "torneo-estivo"
    transaction.set.assert_any_call(
        slugs_ref.document("torneo-estivo"),
        {"tournament_id": "uuid-1"},
    )
    transaction.set.assert_any_call(t_ref, {**doc_data, "slug": "torneo-estivo"})


def test_reserve_slug_with_collision():
    """When slug exists, appends -2."""
    transaction = MagicMock()
    snap_exists = MagicMock()
    snap_exists.exists = True
    snap_free = MagicMock()
    snap_free.exists = False
    transaction.get.side_effect = [snap_exists, snap_free]

    slugs_ref = MagicMock()
    t_ref = MagicMock()
    doc_data = {"name": "Torneo", "admin_uid": "uid-123", "status": "draft"}

    result = reserve_slug_in_transaction(transaction, slugs_ref, "torneo-estivo", "uuid-1", t_ref, doc_data)

    assert result == "torneo-estivo-2"
    transaction.set.assert_any_call(
        slugs_ref.document("torneo-estivo-2"),
        {"tournament_id": "uuid-1"},
    )
    transaction.set.assert_any_call(t_ref, {**doc_data, "slug": "torneo-estivo-2"})


def test_reserve_slug_with_double_collision():
    """When slug and -2 exist, uses -3."""
    transaction = MagicMock()
    snap_exists = MagicMock()
    snap_exists.exists = True
    snap_free = MagicMock()
    snap_free.exists = False
    transaction.get.side_effect = [snap_exists, snap_exists, snap_free]

    slugs_ref = MagicMock()
    t_ref = MagicMock()
    doc_data = {"name": "Torneo", "admin_uid": "uid-123", "status": "draft"}

    result = reserve_slug_in_transaction(transaction, slugs_ref, "torneo-estivo", "uuid-1", t_ref, doc_data)

    assert result == "torneo-estivo-3"
    transaction.set.assert_any_call(
        slugs_ref.document("torneo-estivo-3"),
        {"tournament_id": "uuid-1"},
    )
    transaction.set.assert_any_call(t_ref, {**doc_data, "slug": "torneo-estivo-3"})


def test_generate_slug_sanitizes_date():
    """Non-ISO date characters are sanitised the same as name characters."""
    assert generate_slug("Torneo", "2026/07/15") == "torneo-2026-07-15"
