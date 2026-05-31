import pytest
from pydantic import ValidationError
from schema_engine import build_team_model, sanitize

SCHEMA = {
    "team_fields": [
        {"key": "name", "type": "text", "required": True, "max_length": 10},
        {"key": "contact_email", "type": "email", "required": True},
        {"key": "score", "type": "number", "required": False},
        {"key": "birth_date", "type": "date", "required": False},
    ]
}

def test_valid_data_passes():
    Model = build_team_model(SCHEMA)
    instance = Model(name="Leoni", contact_email="a@b.com")
    assert instance.name == "Leoni"

def test_name_too_long_fails():
    Model = build_team_model(SCHEMA)
    with pytest.raises(ValidationError):
        Model(name="A" * 11, contact_email="a@b.com")

def test_invalid_email_fails():
    Model = build_team_model(SCHEMA)
    with pytest.raises(ValidationError):
        Model(name="Leoni", contact_email="not-an-email")

def test_optional_number_field_absent_passes():
    Model = build_team_model(SCHEMA)
    instance = Model(name="Leoni", contact_email="a@b.com")
    assert instance.score is None

def test_date_field_accepts_date_object():
    from datetime import date
    Model = build_team_model(SCHEMA)
    instance = Model(name="Leoni", contact_email="a@b.com", birth_date=date(2000, 1, 15))
    assert instance.birth_date == date(2000, 1, 15)

def test_sanitize_strips_html():
    assert sanitize("<script>alert(1)</script>Leoni") == "Leoni"

def test_sanitize_preserves_plain_text():
    assert sanitize("Leoni Blu") == "Leoni Blu"
