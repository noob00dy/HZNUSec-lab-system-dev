from datetime import datetime

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )


def fmt(dt, pattern="%Y-%m-%d %H:%M:%S"):
    if not dt:
        return None
    return dt.strftime(pattern)


def fmt_date(d):
    if not d:
        return None
    return d.strftime("%Y-%m-%d")