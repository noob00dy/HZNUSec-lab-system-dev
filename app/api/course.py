"""课程表模块：/api/course/*"""
from flask import Blueprint, request

from app.models import Course, User
from app.utils.response import success

course_bp = Blueprint("course", __name__, url_prefix="/api/course")


def _body():
    return request.get_json(silent=True) or {}


@course_bp.post("/queryCourseByUserList")
def query_course_by_user_list():
    data = _body()
    names = data.get("list") or []
    accounts = []
    for name in names:
        user = (
            User.query.filter_by(account=name).first()
            or User.query.filter_by(user_name=name).first()
        )
        if user:
            accounts.append(user.account)
    if not accounts:
        return success([])
    courses = (
        Course.query.filter(Course.account.in_(accounts))
        .order_by(Course.week.asc())
        .all()
    )
    return success([c.to_dict() for c in courses])