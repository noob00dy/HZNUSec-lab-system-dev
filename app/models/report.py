from app.extensions import db
from app.models.base import TimestampMixin, fmt, fmt_date


class Report(db.Model, TimestampMixin):
    """日报表。"""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    user_name = db.Column(db.String(64))
    group_id = db.Column(db.Integer, index=True)
    report_date = db.Column(db.Date, nullable=False, index=True)
    work_content = db.Column(db.Text, default="")
    problems = db.Column(db.Text, default="")
    plan = db.Column(db.Text, default="")

    __table_args__ = (
        db.UniqueConstraint("account", "report_date", name="uq_report_user_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "userName": self.user_name,
            "groupName": None,
            "reportDate": fmt_date(self.report_date),
            "workContent": self.work_content or "",
            "problems": self.problems or "",
            "plan": self.plan or "",
        }

    def to_timeline(self):
        return {
            "reportDate": fmt_date(self.report_date),
            "workContent": self.work_content or "",
        }