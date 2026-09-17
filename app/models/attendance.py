from app.extensions import db
from app.models.base import TimestampMixin, fmt, fmt_date


class SignRecord(db.Model, TimestampMixin):
    """签到/签退原始记录（每次签到生成一条，签退时补齐 end_time）。"""

    __tablename__ = "sign_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    report_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)

    __table_args__ = (
        db.Index("ix_sign_record_account_date", "account", "report_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "userName": None,
            "groupName": None,
            "startDate": fmt(self.start_time, "%b %d, %Y, %I:%M:%S %p"),
            "endDate": fmt(self.end_time, "%b %d, %Y, %I:%M:%S %p"),
            "reportDate": fmt_date(self.report_date),
        }


class SignDuration(db.Model, TimestampMixin):
    """按人按天聚合的签到时长（小时）。"""

    __tablename__ = "sign_durations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    report_date = db.Column(db.Date, nullable=False, index=True)
    sign_duration = db.Column(db.Float, default=0.0, nullable=False)
    group_id = db.Column(db.Integer, index=True)

    __table_args__ = (
        db.UniqueConstraint("account", "report_date", name="uq_sign_duration_user_date"),
    )

    def to_dict(self):
        return {
            "userName": None,
            "groupName": None,
            "reportDate": fmt_date(self.report_date),
            "signDuration": round(self.sign_duration or 0.0, 1),
        }