from app.extensions import db
from app.models.base import TimestampMixin, fmt_date


class Achievement(db.Model, TimestampMixin):
    """成果记录（学习收获 / 获奖情况）。"""

    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), index=True)
    user_name = db.Column(db.String(64))
    title = db.Column(db.String(255), default="")
    award_date = db.Column(db.Date, index=True)
    content = db.Column(db.Text, default="")
    category = db.Column(db.String(64), default="study")  # study / award

    def to_dict(self):
        return {
            "id": self.id,
            "account": self.account,
            "name": self.user_name,
            "title": self.title,
            "date": fmt_date(self.award_date),
            "content": self.content or "",
            "category": self.category,
        }