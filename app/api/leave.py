"""请假模块：/api/leave/*"""
from flask import Blueprint, request

from app.extensions import db
from app.models import (
    LEAVE_APPROVED,
    LEAVE_PENDING,
    LEAVE_REJECTED,
    Group,
    LeaveRecord,
    User,
)
from app.utils.auth import is_admin, load_current_user, login_required
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, FORBIDDEN, NOT_FOUND, error, success
from app.utils.timeutil import parse_date, parse_datetime

leave_bp = Blueprint("leave", __name__, url_prefix="/api/leave")


def _body():
    return request.get_json(silent=True) or {}


@leave_bp.post("/addLeave")
@login_required
def add_leave():
    data = _body()
    current = load_current_user()
    account = data.get("account") or current.account
    start = parse_datetime(data.get("startDate"))
    end = parse_datetime(data.get("endDate"))
    reason = (data.get("reason") or "").strip()
    if start is None or end is None or not reason:
        return error("请假时间与原因不能为空", code=BAD_REQUEST)
    if end < start:
        return error("结束时间不能早于开始时间", code=BAD_REQUEST)

    user = User.query.filter_by(account=account).first()
    record = LeaveRecord(
        account=account,
        user_name=user.user_name if user else account,
        group_id=user.group_id if user else None,
        report_date=start.date(),
        start_date=start,
        end_date=end,
        reason=reason,
        allowed_flag=LEAVE_PENDING,
    )
    db.session.add(record)
    db.session.commit()
    return success(record.to_dict())


@leave_bp.post("/queryLeaveByPage")
def query_leave_by_page():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = LeaveRecord.query

    user_name = (data.get("userName") or "").strip()
    if user_name:
        query = query.filter(LeaveRecord.user_name.like(f"%{user_name}%"))
    account = data.get("account")
    if account and not user_name:
        query = query.filter(LeaveRecord.account == account)

    state = data.get("state")
    if state not in (None, "", "undefined"):
        try:
            query = query.filter(LeaveRecord.allowed_flag == int(state))
        except (TypeError, ValueError):
            pass

    report_date = parse_date(data.get("reportDate"))
    if report_date:
        query = query.filter(LeaveRecord.report_date == report_date)

    query = query.order_by(LeaveRecord.id.desc())
    items, total = paginate(query, page, size, lambda r: r.to_dict())
    return success(
        {
            "leaveList": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@leave_bp.post("/approveLeave")
@login_required
def approve_leave():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以审批请假", code=FORBIDDEN)
    data = _body()
    record = LeaveRecord.query.get(data.get("id"))
    if record is None:
        return error("请假记录不存在", code=NOT_FOUND)
    record.allowed_flag = LEAVE_APPROVED
    record.handler_account = data.get("handlers") or current.account
    record.handler_name = current.user_name
    db.session.commit()
    return success(record.to_dict())


@leave_bp.post("/notApprovedLeave")
@login_required
def not_approved_leave():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以审批请假", code=FORBIDDEN)
    data = _body()
    record = LeaveRecord.query.get(data.get("id"))
    if record is None:
        return error("请假记录不存在", code=NOT_FOUND)
    remarks = (data.get("remarks") or "").strip()
    if not remarks:
        return error("请输入拒绝原因", code=BAD_REQUEST)
    record.allowed_flag = LEAVE_REJECTED
    record.remarks = remarks
    record.handler_account = data.get("handlers") or current.account
    record.handler_name = current.user_name
    db.session.commit()
    return success(record.to_dict())