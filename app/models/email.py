from app.extensions import db
from app.models.base import TimestampMixin


class EmailGroup(db.Model, TimestampMixin):
    """邮件分组订阅配置。

    某用户（account）订阅某个小组（group_id）的日报，
    可通过 member_account 单独排除某成员（exclude_flag=1）。
    """

    __tablename__ = "email_groups"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), nullable=False, index=True)
    group_id = db.Column(db.Integer, nullable=False, index=True)
    member_account = db.Column(db.String(64))
    exclude_flag = db.Column(db.SmallInteger, default=0, nullable=False)

    def to_dict(self, group_name=None):
        return {
            "id": self.id,
            "groupId": self.group_id,
            "groupName": group_name,
            "memberAccount": self.member_account,
            "excludeFlag": self.exclude_flag,
        }