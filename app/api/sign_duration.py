"""签到时长模块：/api/signDuration/*"""
from flask import Blueprint, request

from app.extensions import db
from app.models import Group, SignDuration, User
from app.services import sign_service
from app.utils.excel import build_workbook, excel_response
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, error, success
from app.utils.timeutil import parse_date

sign_duration_bp = Blueprint("sign_duration", __name__, url_prefix="/api/signDuration")


def _body():
    return request.get_json(silent=True) or {}


def _query(data):
    query = SignDuration.query
    user_name = (data.get("userName") or "").strip()
    group_name = (data.get("groupName") or "").strip()
    if user_name:
        accounts = [
            u.account
            for u in User.query.filter(User.user_name.like(f"%{user_name}%")).all()
        ]
        query = query.filter(SignDuration.account.in_(accounts or ["-"]))
    if group_name:
        group = Group.query.filter_by(group_name=group_name).first()
        accounts = [
            u.account
            for u in User.query.filter_by(group_id=group.group_id if group else -1).all()
        ]
        query = query.filter(SignDuration.account.in_(accounts or ["-"]))
    start = parse_date(data.get("startDate"))
    end = parse_date(data.get("endDate"))
    if start:
        query = query.filter(SignDuration.report_date >= start)
    if end:
        query = query.filter(SignDuration.report_date <= end)
    return query


def _serialize(row, user_map, group_names):
    data = row.to_dict()
    user = user_map.get(row.account)
    data["userName"] = user.user_name if user else row.account
    group_id = user.group_id if user and user.group_id else row.group_id
    data["groupName"] = group_names.get(group_id, "")
    return data


@sign_duration_bp.post("/querySignDurationByPage")
def query_by_page():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = _query(data).order_by(SignDuration.report_date.desc())
    user_map = {u.account: u for u in User.query.all()}
    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    items, total = paginate(
        query, page, size, lambda r: _serialize(r, user_map, group_names)
    )
    return success(
        {
            "list": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@sign_duration_bp.post("/queryWeek")
def query_week():
    data = _body()
    accounts = data.get("list") or []
    names = []
    for item in accounts:
        names.append(item)
    resolved = []
    for name in names:
        user = (
            User.query.filter_by(account=name).first()
            or User.query.filter_by(user_name=name).first()
        )
        if user:
            resolved.append(user.account)
    return success(sign_service.multi_user_week(resolved))


@sign_duration_bp.post("/signDurationDownload")
def download():
    data = _body()
    query = _query(data).order_by(SignDuration.report_date.desc())
    user_map = {u.account: u for u in User.query.all()}
    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    headers = ["姓名", "小组", "日期", "签到时长(小时)"]
    rows = []
    for row in query.all():
        view = _serialize(row, user_map, group_names)
        rows.append([view["userName"], view["groupName"], view["reportDate"], view["signDuration"]])
    buf = build_workbook("签到时长", headers, rows)
    return excel_response(buf, "签到时长报表.xlsx")