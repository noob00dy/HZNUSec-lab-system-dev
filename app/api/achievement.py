"""成果模块：/api/achievement/*"""
from flask import Blueprint, request

from app.models import Achievement, User
from app.utils.pagination import normalize_page, paginate
from app.utils.response import success
from app.utils.timeutil import parse_date

achievement_bp = Blueprint("achievement", __name__, url_prefix="/api/achievement")


def _body():
    return request.get_json(silent=True) or {}


@achievement_bp.post("/study/list")
def study_list():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = Achievement.query.filter_by(category="study")
    name = (data.get("name") or "").strip()
    if name:
        query = query.filter(Achievement.user_name.like(f"%{name}%"))
    day = parse_date(data.get("date"))
    if day:
        query = query.filter(Achievement.award_date == day)
    query = query.order_by(Achievement.award_date.desc(), Achievement.id.desc())
    items, total = paginate(query, page, size, lambda a: a.to_dict())
    return success(
        {
            "list": items,
            "total": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@achievement_bp.post("/award/list")
def award_list():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = Achievement.query.filter_by(category="award")
    name = (data.get("name") or "").strip()
    if name:
        query = query.filter(Achievement.user_name.like(f"%{name}%"))
    query = query.order_by(Achievement.award_date.desc(), Achievement.id.desc())
    items, total = paginate(query, page, size, lambda a: a.to_dict())
    return success(
        {
            "list": items,
            "total": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )