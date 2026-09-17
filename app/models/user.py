from app.extensions import db
from app.models.base import TimestampMixin, fmt, fmt_date


class Role(db.Model):
    """角色表：user / groupLeader / allLeader。"""

    __tablename__ = "roles"

    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.String(64), default="")

    users = db.relationship("User", back_populates="role")

    def to_dict(self):
        return {
            "roleId": self.role_id,
            "roleName": self.role_name,
            "description": self.description or "",
        }


class Group(db.Model, TimestampMixin):
    """小组表。"""

    __tablename__ = "groups"

    group_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_name = db.Column(db.String(64), unique=True, nullable=False)
    leader_account = db.Column(db.String(64), index=True)
    # 是否需要提交日报（旧系统 reportFlag）
    report_flag = db.Column(db.SmallInteger, default=1, nullable=False)

    users = db.relationship("User", back_populates="group")

    def to_dict(self):
        return {
            "groupId": self.group_id,
            "groupName": self.group_name,
            "leaderAccount": self.leader_account,
            "leaderName": None,
            "reportFlag": self.report_flag,
        }


class User(db.Model, TimestampMixin):
    """用户表。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    user_name = db.Column(db.String(64), nullable=False)
    sex = db.Column(db.SmallInteger, default=0)  # 0 男 1 女
    phone = db.Column(db.String(32))
    grade = db.Column(db.String(32))
    email = db.Column(db.String(128))
    group_id = db.Column(db.Integer, db.ForeignKey("groups.group_id"), index=True)
    stu_number = db.Column(db.String(32))
    class_name = db.Column(db.String(64))
    input_date = db.Column(db.Date)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.role_id"), default=1, nullable=False)
    report_flag = db.Column(db.SmallInteger, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    group = db.relationship("Group", back_populates="users")
    role = db.relationship("Role", back_populates="users")

    # ---- 便捷属性 ----
    @property
    def group_name(self):
        return self.group.group_name if self.group else None

    @property
    def role_name(self):
        return self.role.role_name if self.role else None

    @property
    def role_description(self):
        return self.role.description if self.role else None

    def to_brief(self):
        """个人中心 / queryUserMessage 返回。"""
        return {
            "account": self.account,
            "userName": self.user_name,
            "sex": self.sex,
            "phone": self.phone,
            "grade": self.grade,
            "email": self.email,
            "groupName": self.group_name,
            "stuNumber": self.stu_number,
            "className": self.class_name,
            "inputDate": fmt_date(self.input_date),
            "roleName": self.role_name,
            "roleDescription": self.role_description,
            "reportFlag": self.report_flag,
        }

    def to_admin_row(self):
        """人员管理列表返回。"""
        return {
            "account": self.account,
            "userName": self.user_name,
            "groupName": self.group_name,
            "reportFlag": self.report_flag,
            "roleName": self.role_name,
            "roleDescription": self.role_description,
        }