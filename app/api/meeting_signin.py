"""会议签到模块：/api/meetingSignin/*

流程：组织者开启签到 -> 生成二维码 token -> 参会人扫码选择姓名签到 -> 大屏轮询状态。
"""
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, request

from app.extensions import db
from app.models import (
    MEMBER_CHECKED,
    MEMBER_LEAVE,
    Meeting,
    MeetingMember,
    User,
)
from app.utils.auth import load_current_user, login_required
from app.utils.response import BAD_REQUEST, NOT_FOUND, error, success

meeting_signin_bp = Blueprint(
    "meeting_signin", __name__, url_prefix="/api/meetingSignin"
)

SIGNIN_DURATION_MINUTES = 30


def _body():
    return request.get_json(silent=True) or {}


def _board(meeting):
    members = (
        MeetingMember.query.filter_by(meeting_id=meeting.meeting_id)
        .order_by(MeetingMember.id.asc())
        .all()
    )
    return {
        "meetingId": meeting.meeting_id,
        "meetingName": meeting.meeting_name,
        "location": meeting.location,
        "startTime": meeting.start_at.strftime("%Y-%m-%d %H:%M:%S"),
        "signinStatus": meeting.signin_status,
        "signinStartTime": meeting.signin_start_at.strftime("%Y-%m-%d %H:%M:%S")
        if meeting.signin_start_at
        else None,
        "signinEndTime": meeting.signin_end_at.strftime("%Y-%m-%d %H:%M:%S")
        if meeting.signin_end_at
        else None,
        "total": len(members),
        "checkedIn": len([m for m in members if m.checked_in]),
        "members": [m.to_audit() for m in members],
    }


def _refresh_status(meeting):
    if meeting.signin_status == 1 and meeting.signin_end_at:
        if datetime.now() > meeting.signin_end_at:
            meeting.signin_status = 2
            db.session.commit()


@meeting_signin_bp.post("/board")
def board():
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    _refresh_status(meeting)
    return success(_board(meeting))


@meeting_signin_bp.post("/start")
@login_required
def start():
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    if meeting.signin_status == 2:
        return error("本次签到已结束，不能重新开启", code=BAD_REQUEST)
    meeting.signin_status = 1
    meeting.signin_token = uuid.uuid4().hex
    meeting.signin_start_at = datetime.now()
    meeting.signin_end_at = datetime.now() + timedelta(minutes=SIGNIN_DURATION_MINUTES)
    db.session.commit()
    return success(
        {
            "signinPath": f"/meeting/signin/checkin?token={meeting.signin_token}",
            "token": meeting.signin_token,
            "board": _board(meeting),
        }
    )


@meeting_signin_bp.post("/end")
@login_required
def end():
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    meeting.signin_status = 2
    meeting.signin_end_at = datetime.now()
    db.session.commit()
    return success(_board(meeting))


@meeting_signin_bp.post("/status")
@login_required
def status():
    """组织者手动修改某成员签到状态（已签到/请假）。"""
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    member = MeetingMember.query.filter_by(
        meeting_id=meeting.meeting_id, account=data.get("account")
    ).first()
    if member is None:
        return error("该成员不在会议名单中", code=BAD_REQUEST)

    new_status = data.get("status")
    try:
        new_status = int(new_status)
    except (TypeError, ValueError):
        return error("状态非法", code=BAD_REQUEST)

    member.status = new_status
    if new_status == MEMBER_CHECKED:
        member.checked_in = True
        member.check_in_time = member.check_in_time or datetime.now()
        member.leave_reason = ""
    elif new_status == MEMBER_LEAVE:
        member.checked_in = False
        member.check_in_time = None
        member.leave_reason = (data.get("reason") or "").strip()
    else:
        member.checked_in = False
        member.check_in_time = None
    db.session.commit()
    return success(_board(meeting))


@meeting_signin_bp.get("/selection")
def selection():
    """扫码后读取会议信息与候选人员（无需登录）。"""
    token = request.args.get("token")
    if not token:
        return error("缺少 token 参数", code=BAD_REQUEST)
    meeting = Meeting.query.filter_by(signin_token=token).first()
    if meeting is None:
        return error("签到链接无效", code=NOT_FOUND)
    _refresh_status(meeting)
    members = (
        MeetingMember.query.filter_by(meeting_id=meeting.meeting_id)
        .order_by(MeetingMember.id.asc())
        .all()
    )
    people = []
    for member in members:
        user = User.query.filter_by(account=member.account).first()
        group_name = user.group.group_name if user and user.group else ""
        people.append(
            {
                "account": member.account,
                "userName": member.user_name or member.account,
                "department": group_name,
                "checkedIn": bool(member.checked_in),
            }
        )
    return success(
        {
            "meetingId": meeting.meeting_id,
            "meetingName": meeting.meeting_name,
            "reportDate": meeting.report_date.strftime("%Y-%m-%d"),
            "location": meeting.location,
            "signinStatus": meeting.signin_status,
            "signinEndTime": meeting.signin_end_at.strftime("%Y-%m-%d %H:%M:%S")
            if meeting.signin_end_at
            else None,
            "people": people,
        }
    )


@meeting_signin_bp.post("/complete")
def complete():
    """参会人提交签到（无需登录）。"""
    data = _body()
    token = data.get("token")
    account = data.get("account")
    if not token or not account:
        return error("参数不完整", code=BAD_REQUEST)
    meeting = Meeting.query.filter_by(signin_token=token).first()
    if meeting is None:
        return error("签到链接无效", code=NOT_FOUND)
    _refresh_status(meeting)
    if meeting.signin_status != 1:
        return error("签到已结束", code=BAD_REQUEST)

    member = MeetingMember.query.filter_by(
        meeting_id=meeting.meeting_id, account=account
    ).first()
    if member is None:
        return error("你不在本次会议名单中", code=BAD_REQUEST)
    if member.checked_in:
        return success({"userName": member.user_name, "alreadyCheckedIn": True})

    member.checked_in = True
    member.status = MEMBER_CHECKED
    member.check_in_time = datetime.now()
    db.session.commit()
    return success(
        {
            "userName": member.user_name or member.account,
            "checkInTime": member.check_in_time.strftime("%Y-%m-%d %H:%M:%S"),
            "alreadyCheckedIn": False,
        }
    )