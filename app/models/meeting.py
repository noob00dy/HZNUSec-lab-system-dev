from app.extensions import db
from app.models.base import TimestampMixin, fmt, fmt_date

# 会议成员签到状态
MEMBER_NORMAL = 0      # 未签到
MEMBER_CHECKED = 1     # 已签到
MEMBER_LEAVE = 2       # 请假


class Meeting(db.Model, TimestampMixin):
    """会议表。"""

    __tablename__ = "meetings"

    meeting_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    meeting_name = db.Column(db.String(128), nullable=False)
    report_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, default="")
    start_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(128))
    organizer_account = db.Column(db.String(64), index=True)
    organizer_name = db.Column(db.String(64))
    status = db.Column(db.SmallInteger, default=0)  # 0 未开始 1 进行中 2 已结束
    summary = db.Column(db.Text, default="")
    keyword = db.Column(db.String(255), default="")

    # 会议签到（二维码）
    signin_status = db.Column(db.SmallInteger, default=0)  # 0 未开启 1 进行中 2 已结束
    signin_token = db.Column(db.String(64), index=True)
    signin_start_at = db.Column(db.DateTime)
    signin_end_at = db.Column(db.DateTime)

    members = db.relationship(
        "MeetingMember", back_populates="meeting", cascade="all, delete-orphan"
    )

    def to_dict(self, files=None):
        return {
            "meetingId": self.meeting_id,
            "meetingName": self.meeting_name,
            "reportDate": fmt_date(self.report_date),
            "description": self.description or "",
            "startTime": fmt(self.start_at, "%H:%M:%S"),
            "location": self.location or "",
            "organizerAccount": self.organizer_account,
            "organizerName": self.organizer_name or "",
            "membersName": ", ".join(m.user_name or m.account for m in self.members),
            "status": self.status,
            "summary": self.summary or "",
            "keyword": self.keyword or "",
            "files": [f.to_meeting_file() for f in (files or [])],
            "signinStatus": self.signin_status,
            "signinStartTime": fmt(self.signin_start_at),
            "signinEndTime": fmt(self.signin_end_at),
        }


class MeetingMember(db.Model, TimestampMixin):
    """会议参会成员及签到状态。"""

    __tablename__ = "meeting_members"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    meeting_id = db.Column(
        db.Integer, db.ForeignKey("meetings.meeting_id"), nullable=False, index=True
    )
    account = db.Column(db.String(64), nullable=False, index=True)
    user_name = db.Column(db.String(64))
    group_id = db.Column(db.Integer)
    checked_in = db.Column(db.Boolean, default=False, nullable=False)
    check_in_time = db.Column(db.DateTime)
    status = db.Column(db.SmallInteger, default=MEMBER_NORMAL, nullable=False)
    leave_reason = db.Column(db.String(255), default="")

    meeting = db.relationship("Meeting", back_populates="members")

    __table_args__ = (
        db.UniqueConstraint("meeting_id", "account", name="uq_meeting_member"),
    )

    def to_audit(self):
        status = self.status
        if status == MEMBER_LEAVE:
            label = "请假"
        elif self.checked_in:
            label = "已签到"
        else:
            label = "未签到"
        return {
            "account": self.account,
            "userName": self.user_name or self.account,
            "hasCheckedIn": bool(self.checked_in),
            "checkInTime": fmt(self.check_in_time),
            "status": status,
            "statusLabel": label,
            "leaveReason": self.leave_reason or "",
        }