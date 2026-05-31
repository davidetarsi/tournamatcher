from __future__ import annotations
from datetime import date
from typing import Annotated, Optional
from pydantic import create_model, EmailStr
from pydantic import StringConstraints
import nh3


def build_team_model(schema: dict):
    """Genera un modello Pydantic dinamico dai team_fields dello schema."""
    fields: dict = {}
    for f in schema["team_fields"]:
        required = f.get("required", True)

        if f["type"] == "text":
            max_len = f.get("max_length", 200)
            annotation = Annotated[str, StringConstraints(max_length=max_len)]
        elif f["type"] == "email":
            annotation = EmailStr
        elif f["type"] == "number":
            annotation = int
        elif f["type"] == "date":
            annotation = date
        else:
            continue

        if required:
            fields[f["key"]] = (annotation, ...)
        else:
            fields[f["key"]] = (Optional[annotation], None)

    return create_model("TeamData", **fields)


def sanitize(value: str) -> str:
    """Rimuove tutti i tag HTML dal testo."""
    return nh3.clean(value, tags=set())
