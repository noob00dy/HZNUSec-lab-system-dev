"""用户模块：/api/user/*"""
from flask import Blueprint, request
from sqlalchemy import or_

from app.extensions import db
from app.models import Report, Role, User
from app.services.summary_service import generate_personal_summary
from app.utils.auth import can_manage_group, is_admin, load_current_user, login_required
from app.utils.excel import build_workbook, excel_response
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, FORBIDDEN, error, success

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


def _body():
    return request.get_json(silent=True) or {}


@user_bp.post("/queryUserMessage")
def query_user_message():
    data = _body()
    account = data.get("account") or (load_current_user().account if load_current_user() else None)
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    user = User.query.filter_by(account=account).first()
    if user is None:
        return error("用户不存在", code=BAD_REQUEST)
    return success(user.to_brief())


@user_bp.post("/queryUserByPage")
@login_required
def query_user_by_page():
    data = _body()
    operator = data.get("operator") or ""
    current = load_current_user()
    if not (is_admin(current) or (operator and operator == current.account and current.role_name == "groupLeader")):
        return error("没有人员管理权限", code=FORBIDDEN)

    page, size = normalize_page(data.get("page"), data.get("size"))
    query = User.query
    user_name = (data.get("userName") or "").strip()
    group_name = (data.get("groupName") or "").strip()
    if user_name:
        query = query.filter(
            or_(User.user_name.like(f"%{user_name}%"), User.account.like(f"%{user_name}%"))
        )
    if group_name:
        from app.models import Group

        group = Group.query.filter_by(group_name=group_name).first()
        if group:
            query = query.filter(User.group_id == group.group_id)
        else:
            query = query.filter(db.false())
    if not is_admin(current):
        query = query.filter(User.group_id == current.group_id)

    query = query.order_by(User.id.asc())
    items, total = paginate(query, page, size, lambda u: u.to_admin_row())
    return success(
        {
            "userList": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@user_bp.post("/queryGroupUserAll")
@login_required
def query_group_user_all():
    from app.models import Group

    groups = Group.query.order_by(Group.group_id.asc()).all()
    result = []
    for group in groups:
        members = User.query.filter_by(group_id=group.group_id).all()
        result.append(
            {
                "groupName": group.group_name,
                "userList": [m.user_name for m in members],
            }
        )
    return success(result)


@user_bp.post("/queryRoleList")
def query_role_list():
    roles = Role.query.order_by(Role.role_id.asc()).all()
    return success([r.to_dict() for r in roles])


@user_bp.post("/updateUser")
@login_required
def update_user():
    data = _body()
    current = load_current_user()
    operator = data.get("operator") or ""
    account = data.get("account")
    user = User.query.filter_by(account=account).first()
    if user is None:
        return error("用户不存在", code=BAD_REQUEST)
    if not (is_admin(current) or operator == current.account):
        return error("没有修改权限", code=FORBIDDEN)

    from app.models import Group

    group_name = data.get("groupName")
    if group_name is not None:
        group = Group.query.filter_by(group_name=group_name).first()
        user.group_id = group.group_id if group else None
    if "reportFlag" in data and is_admin(current):
        try:
            user.report_flag = int(data.get("reportFlag") or 0)
        except (TypeError, ValueError):
            pass
    db.session.commit()
    return success(user.to_admin_row())


@user_bp.post("/deleteUser")
@login_required
def delete_user():
    data = _body()
    current = load_current_user()
    operator = data.get("operator") or ""
    if not (is_admin(current) or operator == current.account):
        return error("没有删除权限", code=FORBIDDEN)
    user = User.query.filter_by(account=data.get("account")).first()
    if user is None:
        return error("用户不存在", code=BAD_REQUEST)
    if user.account == current.account:
        return error("不能删除当前登录账号", code=BAD_REQUEST)
    db.session.delete(user)
    db.session.commit()
    return success(None)


@user_bp.post("/appointGroupLeader")
@login_required
def appoint_group_leader():
    data = _body()
    current = load_current_user()
    from app.models import Group

    group = Group.query.filter_by(group_name=data.get("groupName")).first()
    target = User.query.filter_by(account=data.get("account")).first()
    if group is None or target is None:
        return error("小组或用户不存在", code=BAD_REQUEST)
    if not (is_admin(current) or can_manage_group(current, group.group_id)):
        return error("没有任命权限", code=FORBIDDEN)

    # 原组长恢复为普通成员
    User.query.filter_by(group_id=group.group_id, role_id=2).update({"role_id": 1})
    target.group_id = group.group_id
    target.role_id = 2
    group.leader_account = target.account
    db.session.commit()
    return success(None)


@user_bp.post("/updateUserRole")
@login_required
def update_user_role():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以调整角色", code=FORBIDDEN)
    data = _body()
    user = User.query.filter_by(account=data.get("account")).first()
    role = Role.query.filter_by(role_id=data.get("roleId")).first()
    if user is None or role is None:
        return error("用户或角色不存在", code=BAD_REQUEST)
    user.role_id = role.role_id
    db.session.commit()
    return success(None)


@user_bp.post("/timeline")
def timeline():
    data = _body()
    account = data.get("account")
    year = data.get("year")
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    query = Report.query.filter(Report.account == account)
    if year:
        try:
            query = query.filter(db.extract("year", Report.report_date) == int(year))
        except (TypeError, ValueError):
            pass
    reports = query.order_by(Report.report_date.desc()).all()
    return success([r.to_timeline() for r in reports])


@user_bp.post("/generatePersonalSummary")
@login_required
def generate_summary():
    data = _body()
    account = data.get("account") or load_current_user().account
    content = generate_personal_summary(account)
    if content is None:
        return error("用户不存在", code=BAD_REQUEST)
    return success({"summary": content})


@user_bp.post("/download")
@login_required
def download_users():
    data = _body()
    query = User.query
    user_name = (data.get("userName") or "").strip()
    group_name = (data.get("groupName") or "").strip()
    if user_name:
        query = query.filter(User.user_name.like(f"%{user_name}%"))
    if group_name:
        from app.models import Group

        group = Group.query.filter_by(group_name=group_name).first()
        query = query.filter(User.group_id == (group.group_id if group else -1))
    headers = ["账号", "姓名", "小组", "学号", "班级", "年级", "手机", "邮箱", "角色"]
    rows = [
        [
            u.account,
            u.user_name,
            u.group_name or "",
            u.stu_number or "",
            u.class_name or "",
            u.grade or "",
            u.phone or "",
            u.email or "",
            u.role_name or "",
        ]
        for u in query.order_by(User.id.asc()).all()
    ]
    buf = build_workbook("人员统计", headers, rows)
    return excel_response(buf, "用户统计报表.xlsx")