from app.extensions import db
from app.models.base import TimestampMixin


class SystemConfig(db.Model, TimestampMixin):
    """系统配置键值表。

    已知配置：
      report_type      0 不发送邮件 / 1 日报 / 2 周报
      skip_holidays    0 不跳过节假日 / 1 跳过节假日
    """

    __tablename__ = "system_configs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False)
    config_value = db.Column(db.String(255), default="")
    description = db.Column(db.String(255), default="")

    REPORT_TYPE = "report_type"
    SKIP_HOLIDAYS = "skip_holidays"

    @classmethod
    def get_value(cls, key, default=None):
        row = cls.query.filter_by(config_key=key).first()
        return row.config_value if row else default

    @classmethod
    def set_value(cls, key, value, description=None):
        row = cls.query.filter_by(config_key=key).first()
        if row is None:
            row = cls(config_key=key, description=description or "")
            db.session.add(row)
        row.config_value = str(value)
        if description:
            row.description = description
        return row


class HomeReminder(db.Model, TimestampMixin):
    """首页提醒（日报超期、签到时长不足等）。"""

    __tablename__ = "home_reminders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    reminder_type = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(128), default="")
    message = db.Column(db.String(512), default="")
    cycle_key = db.Column(db.String(64), default="")
    is_acknowledged = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "account", "reminder_type", "cycle_key", name="uq_reminder_cycle"
        ),
    )

    def to_dict(self):
        return {
            "reminderType": self.reminder_type,
            "title": self.title,
            "message": self.message,
            "cycleKey": self.cycle_key,
        }