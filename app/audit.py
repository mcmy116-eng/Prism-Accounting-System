"""Audit trail helper.

Records an append-only log of significant actions (who, what, when) so the
books have a defensible change history for accountant / auditor review.

Call ``record(...)`` inside a request while a user is logged in; it adds the
row to the current session but does not commit — the surrounding transaction
that made the change owns the commit, keeping the log consistent with the data.
"""
import json

from flask_login import current_user

from app.extensions import db
from app.models import AuditLog


def record(action, entity_type, entity_id=None, summary="", detail=None):
    user_id = getattr(current_user, "id", None) if current_user else None
    user_name = getattr(current_user, "name", "") if current_user else ""
    log = AuditLog(
        user_id=user_id,
        user_name=user_name or "system",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary[:400],
        detail=json.dumps(detail) if detail is not None else "",
    )
    db.session.add(log)
    return log
