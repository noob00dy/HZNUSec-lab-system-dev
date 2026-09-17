from app.extensions import db
from app.models.base import TimestampMixin, fmt, fmt_date

LEAVE_PENDING = 0   # 待审核
LEAVE_APPROVED = 1  # 已通过
LEAVE_REJECTED = 2  # 已拒绝


class LeaveRecord(db.Model, TimestampMixin):
    """请假记录。"""

    __tablename__ = "leave_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    user_name = db.Column(db.String(64))
    group_id = db.Column(db.Integer, index=True)
    report_date = db.Column(db.Date, nullable=False, index=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, default="")
    remarks = db.Column(db.String(255), default="")
    allowed_flag = db.Column(db.SmallInteger, default=LEAVE_PENDING, nullable=False)
    handler_account = db.Column(db.String(64))
    handler_name = db.Column(db.String(64))

    def to_dict(self):
        label = {0: "待审核", 1: "已通过", 2: "已拒绝"}.get(self.allowed_flag, "未知")
        return {
            "id": self.id,
            "reportDate": fmt_date(self.report_date),
            "startDate": fmt(self.start_date),
            "endDate": fmt(self.end_date),
            "userName": self.user_name or self.account,
            "reason": self.reason or "",
            "remarks": self.remarks or "",
            "allowedFlag": self.allowed_flag,
            "allowedLabel": label,
        }