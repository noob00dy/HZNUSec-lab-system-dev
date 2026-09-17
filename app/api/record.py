"""签到记录模块：/api/record/*"""
from flask import Blueprint, request

from app.extensions import db
from app.models import Group, SignRecord, User
from app.services import sign_service
from app.utils.auth import load_current_user, login_required
from app.utils.excel import build_workbook, excel_response
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, error, success
from app.utils.timeutil import parse_date

record_bp = Blueprint("record", __name__, url_prefix="/api/record")


def _body():
    return request.get_json(silent=True) or {}


def _account_or_current(data):
    return data.get("account") or (load_current_user().account if load_current_user() else None)


@record_bp.post("/checkIn")
def check_in():
    data = _body()
    account = _account_or_current(data)
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    ok, message = sign_service.check_in(account)
    return success({"statusType": sign_service.current_status(account)}, msg=message) if ok else error(message, code=BAD_REQUEST)


@record_bp.post("/checkOut")
def check_out():
    data = _body()
    account = _account_or_current(data)
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    ok, message = sign_service.check_out(account)
    return success({"statusType": sign_service.current_status(account)}, msg=message) if ok else error(message, code=BAD_REQUEST)


@record_bp.post("/queryStatusType")
def query_status_type():
    data = _body()
    account = _account_or_current(data)
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    return success({"statusType": sign_service.current_status(account)})


def _record_query(data):
    query = SignRecord.query
    account = data.get("account")
    if account:
        query = query.filter(SignRecord.account == account)
    user_name = (data.get("userName") or "").strip()
    group_name = (data.get("groupName") or "").strip()
    if user_name:
        accounts = [
            u.account
            for u in User.query.filter(User.user_name.like(f"%{user_name}%")).all()
        ]
        query = query.filter(SignRecord.account.in_(accounts or ["-"]))
    if group_name:
        group = Group.query.filter_by(group_name=group_name).first()
        accounts = [
            u.account
            for u in User.query.filter_by(group_id=group.group_id if group else -1).all()
        ]
        query = query.filter(SignRecord.account.in_(accounts or ["-"]))
    start = parse_date(data.get("startDate"))
    end = parse_date(data.get("endDate"))
    if start:
        query = query.filter(SignRecord.report_date >= start)
    if end:
        query = query.filter(SignRecord.report_date <= end)
    return query


def _serialize_record(record, user_map, group_names):
    data = record.to_dict()
    user = user_map.get(record.account)
    data["userName"] = user.user_name if user else record.account
    data["groupName"] = group_names.get(user.group_id) if user and user.group_id else ""
    return data


@record_bp.post("/queryRecordByPage")
def query_record_by_page():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = _record_query(data).order_by(
        SignRecord.report_date.desc(), SignRecord.start_time.desc()
    )
    user_map = {u.account: u for u in User.query.all()}
    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    items, total = paginate(
        query, page, size, lambda r: _serialize_record(r, user_map, group_names)
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


@record_bp.post("/querySignDurationWeek")
def query_sign_duration_week():
    data = _body()
    account = _account_or_current(data)
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    return success(sign_service.week_durations(account))


@record_bp.post("/queryGroupSignDuration")
def query_group_sign_duration():
    data = _body()
    start = parse_date(data.get("startDate"))
    end = parse_date(data.get("endDate"))
    return success(sign_service.group_totals(start, end))


@record_bp.post("/checkInRecordDownload")
def download_records():
    data = _body()
    query = _record_query(data).order_by(
        SignRecord.report_date.desc(), SignRecord.start_time.desc()
    )
    user_map = {u.account: u for u in User.query.all()}
    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    headers = ["姓名", "小组", "日期", "签到时间", "签退时间"]
    rows = []
    for record in query.all():
        user = user_map.get(record.account)
        rows.append(
            [
                user.user_name if user else record.account,
                group_names.get(user.group_id) if user and user.group_id else "",
                record.report_date.strftime("%Y-%m-%d"),
                record.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                record.end_time.strftime("%Y-%m-%d %H:%M:%S") if record.end_time else "",
            ]
        )
    buf = build_workbook("签到记录", headers, rows)
    return excel_response(buf, "签到记录.xlsx")