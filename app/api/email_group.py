"""邮件分组模块：/api/emailGroup/*"""
from flask import Blueprint, request

from app.extensions import db
from app.models import EmailGroup, Group, User
from app.utils.auth import is_admin, load_current_user, login_required
from app.utils.response import BAD_REQUEST, FORBIDDEN, error, success

email_group_bp = Blueprint("email_group", __name__, url_prefix="/api/emailGroup")


def _body():
    return request.get_json(silent=True) or {}


@email_group_bp.post("/queryEmailGroup")
@login_required
def query_email_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以配置邮件", code=FORBIDDEN)

    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    users = User.query.order_by(User.id.asc()).all()
    result = []
    for user in users:
        subscriptions = EmailGroup.query.filter_by(account=user.account).all()
        if not subscriptions and not user.email:
            continue
        result.append(
            {
                "account": user.account,
                "userName": user.user_name,
                "email": user.email or "",
                "groupList": [
                    s.to_dict(group_names.get(s.group_id)) for s in subscriptions
                ],
            }
        )
    return success(result)


@email_group_bp.post("/addEmailGroupByUser")
@login_required
def add_email_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以配置邮件", code=FORBIDDEN)
    data = _body()
    account = data.get("account")
    group_id = data.get("groupId")
    if not account or not group_id:
        return error("账号与小组不能为空", code=BAD_REQUEST)
    row = EmailGroup(
        account=account,
        group_id=int(group_id),
        member_account=data.get("memberAccount"),
        exclude_flag=int(data.get("excludeFlag") or 0),
    )
    db.session.add(row)
    db.session.commit()
    return success({"id": row.id})


@email_group_bp.post("/updateEmailGroupByUser")
@login_required
def update_email_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以配置邮件", code=FORBIDDEN)
    data = _body()
    row = EmailGroup.query.get(data.get("id"))
    if row is None:
        return error("配置不存在", code=BAD_REQUEST)
    if "groupId" in data:
        row.group_id = int(data["groupId"])
    if "memberAccount" in data:
        row.member_account = data.get("memberAccount")
    if "excludeFlag" in data:
        row.exclude_flag = int(data.get("excludeFlag") or 0)
    db.session.commit()
    return success(None)


@email_group_bp.post("/deleteEmailGroupByUser")
@login_required
def delete_email_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以配置邮件", code=FORBIDDEN)
    data = _body()
    row = EmailGroup.query.get(data.get("id"))
    if row is None:
        return error("配置不存在", code=BAD_REQUEST)
    db.session.delete(row)
    db.session.commit()
    return success(None)