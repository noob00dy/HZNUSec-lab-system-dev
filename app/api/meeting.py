"""会议模块：/api/meeting/*、/api/userMeeting/*"""
from flask import Blueprint, current_app, request

from app.extensions import db
from app.models import FileRecord, Group, Meeting, MeetingMember, User
from app.services.summary_service import generate_meeting_minutes
from app.utils.auth import load_current_user, login_required
from app.utils.excel import build_workbook, excel_response
from app.utils.files import save_upload
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, NOT_FOUND, error, success
from app.utils.timeutil import parse_date, parse_datetime

meeting_bp = Blueprint("meeting", __name__, url_prefix="/api/meeting")
user_meeting_bp = Blueprint("user_meeting", __name__, url_prefix="/api/userMeeting")


def _body():
    return request.get_json(silent=True) or {}


def _files_of(meeting_id):
    return (
        FileRecord.query.filter_by(source_type=2, related_id=meeting_id)
        .order_by(FileRecord.id.desc())
        .all()
    )


def _serialize(meeting):
    return meeting.to_dict(files=_files_of(meeting.meeting_id))


@meeting_bp.post("/addMeeting")
@login_required
def add_meeting():
    data = _body()
    current = load_current_user()
    if current.role_name not in ("allLeader", "groupLeader"):
        return error("没有发布会议权限", code="403")

    meeting_name = (data.get("meetingName") or "").strip()
    start_at = parse_datetime(data.get("startTime"))
    if not meeting_name or start_at is None:
        return error("会议名称和会议时间不能为空", code=BAD_REQUEST)

    organizer_account = data.get("organizerAccount") or current.account
    organizer = User.query.filter_by(account=organizer_account).first()

    meeting = Meeting(
        meeting_name=meeting_name,
        report_date=start_at.date(),
        description=data.get("description", ""),
        start_at=start_at,
        location=data.get("location", ""),
        organizer_account=organizer_account,
        organizer_name=organizer.user_name if organizer else None,
        status=0,
    )
    db.session.add(meeting)
    db.session.flush()

    member_names = data.get("memberList") or []
    for name in member_names:
        user = (
            User.query.filter_by(user_name=name).first()
            or User.query.filter_by(account=name).first()
        )
        if user is None:
            continue
        db.session.add(
            MeetingMember(
                meeting_id=meeting.meeting_id,
                account=user.account,
                user_name=user.user_name,
                group_id=user.group_id,
            )
        )
    db.session.commit()
    return success(_serialize(meeting))


@meeting_bp.post("/queryMeetingByPage")
def query_meeting_by_page():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = Meeting.query
    name = (data.get("meetingName") or "").strip()
    if name:
        query = query.filter(Meeting.meeting_name.like(f"%{name}%"))
    report_date = parse_date(data.get("reportDate"))
    if report_date:
        query = query.filter(Meeting.report_date == report_date)
    query = query.order_by(Meeting.report_date.desc(), Meeting.meeting_id.desc())
    items, total = paginate(query, page, size, _serialize)
    return success(
        {
            "MeetingsList": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@meeting_bp.post("/queryMeetingByDate")
def query_meeting_by_date():
    data = _body()
    account = data.get("account")
    day = parse_date(data.get("queryDate"))
    if day is None:
        return success([])
    query = Meeting.query.filter(Meeting.report_date == day)
    if account:
        meeting_ids = [
            m.meeting_id
            for m in MeetingMember.query.filter_by(account=account).all()
        ]
        query = query.filter(
            db.or_(
                Meeting.meeting_id.in_(meeting_ids or [-1]),
                Meeting.organizer_account == account,
            )
        )
    meetings = query.order_by(Meeting.start_at.asc()).all()
    return success([_serialize(m) for m in meetings])


@meeting_bp.post("/updateSummary")
@login_required
def update_summary():
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    if not _can_manage_meeting(load_current_user(), meeting):
        return error("没有权限", code="403")
    meeting.summary = (data.get("summary") or "").strip()
    db.session.commit()
    return success(None)


@meeting_bp.post("/updateKeyword")
@login_required
def update_keyword():
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    if not _can_manage_meeting(load_current_user(), meeting):
        return error("没有权限", code="403")
    meeting.keyword = (data.get("keyword") or "").strip()
    db.session.commit()
    return success(None)


@meeting_bp.post("/getMeetingMinutes")
@login_required
def get_meeting_minutes():
    data = _body()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    if not _can_manage_meeting(load_current_user(), meeting):
        return error("没有权限", code="403")
    content = generate_meeting_minutes(meeting)
    return success({"summary": content})


@meeting_bp.post("/queryMeetingAttendanceAudit")
def query_meeting_attendance_audit():
    data = _body()
    meeting_id = data.get("meetingId")
    members = (
        MeetingMember.query.filter_by(meeting_id=meeting_id)
        .order_by(MeetingMember.id.asc())
        .all()
    )
    return success([m.to_audit() for m in members])


@meeting_bp.post("/uploadReport")
@login_required
def upload_report():
    current = load_current_user()
    meeting_id = request.form.get("meetingId") or request.args.get("meetingId")
    meeting = Meeting.query.get(meeting_id)
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    files = request.files.getlist("files")
    if not files:
        return error("未选择文件", code=BAD_REQUEST)
    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue
        record, _ = save_upload(
            file_storage,
            subdir="meetings",
            upload_folder=current_app.config["UPLOAD_FOLDER"],
            account=current.account,
            user_name=current.user_name,
            source_type=2,
            related_id=meeting.meeting_id,
        )
        db.session.add(record)
    db.session.commit()
    return success(None)


@meeting_bp.post("/download")
def download_meetings():
    data = _body()
    query = Meeting.query
    name = (data.get("meetingName") or "").strip()
    if name:
        query = query.filter(Meeting.meeting_name.like(f"%{name}%"))
    day = parse_date(data.get("reportDate"))
    if day:
        query = query.filter(Meeting.report_date == day)
    headers = ["会议名称", "日期", "开始时间", "地点", "组织人", "参会人员", "状态"]
    rows = []
    for meeting in query.order_by(Meeting.report_date.desc()).all():
        members = MeetingMember.query.filter_by(meeting_id=meeting.meeting_id).all()
        rows.append(
            [
                meeting.meeting_name,
                meeting.report_date.strftime("%Y-%m-%d"),
                meeting.start_at.strftime("%H:%M:%S"),
                meeting.location or "",
                meeting.organizer_name or "",
                "、".join(m.user_name or m.account for m in members),
                meeting.status,
            ]
        )
    buf = build_workbook("会议记录", headers, rows)
    return excel_response(buf, "会议记录.xlsx")


def _can_manage_meeting(user, meeting):
    if user is None:
        return False
    if user.role_name == "allLeader":
        return True
    if meeting.organizer_account == user.account:
        return True
    return user.role_name == "groupLeader" and user.group_id is not None


@user_meeting_bp.post("/leaveMeeting")
@login_required
def leave_meeting():
    data = _body()
    current = load_current_user()
    meeting = Meeting.query.get(data.get("meetingId"))
    if meeting is None:
        return error("会议不存在", code=NOT_FOUND)
    member = MeetingMember.query.filter_by(
        meeting_id=meeting.meeting_id, account=current.account
    ).first()
    if member is None:
        member = MeetingMember(
            meeting_id=meeting.meeting_id,
            account=current.account,
            user_name=current.user_name,
            group_id=current.group_id,
        )
        db.session.add(member)
    member.status = 2
    member.leave_reason = (data.get("reason") or "").strip()
    db.session.commit()
    return success(None)