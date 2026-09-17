"""小组模块：/api/group/*"""
from flask import Blueprint, request

from app.extensions import db
from app.models import Group, User
from app.utils.auth import can_manage_group, is_admin, load_current_user, login_required
from app.utils.excel import build_workbook, excel_response
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, FORBIDDEN, error, success

group_bp = Blueprint("group", __name__, url_prefix="/api/group")


def _body():
    return request.get_json(silent=True) or {}


@group_bp.post("/queryGroupsList")
def query_groups_list():
    groups = Group.query.order_by(Group.group_id.asc()).all()
    return success([g.group_name for g in groups])


@group_bp.post("/queryGroupsByPage")
@login_required
def query_groups_by_page():
    current = load_current_user()
    if not is_admin(current):
        return error("只能总管人员可以管理小组", code=FORBIDDEN)
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = Group.query.order_by(Group.group_id.asc())
    items, total = paginate(query, page, size, _serialize_group)
    return success(
        {
            "grouplist": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


def _serialize_group(group):
    leader = User.query.filter_by(account=group.leader_account).first()
    data = group.to_dict()
    data["leaderName"] = leader.user_name if leader else None
    data["memberCount"] = User.query.filter_by(group_id=group.group_id).count()
    return data


@group_bp.post("/queryManageableGroups")
@login_required
def query_manageable_groups():
    current = load_current_user()
    if is_admin(current):
        groups = Group.query.order_by(Group.group_id.asc()).all()
    elif current.role_name == "groupLeader":
        groups = Group.query.filter_by(group_id=current.group_id).all()
    else:
        return error("没有小组成员管理权限", code=FORBIDDEN)
    return success([g.group_name for g in groups])


@group_bp.post("/addGroup")
@login_required
def add_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以新增小组", code=FORBIDDEN)
    data = _body()
    group_name = (data.get("groupName") or "").strip()
    if not group_name:
        return error("请设置组名", code=BAD_REQUEST)
    if Group.query.filter_by(group_name=group_name).first():
        return error("小组已存在", code=BAD_REQUEST)

    report_flag = 1
    try:
        report_flag = int(data.get("reportFlag", 1))
    except (TypeError, ValueError):
        pass

    group = Group(group_name=group_name, report_flag=report_flag)
    db.session.add(group)
    db.session.flush()

    leader_name = (data.get("leaderName") or "").strip()
    if leader_name:
        leader = User.query.filter_by(user_name=leader_name).first()
        if leader is None:
            db.session.rollback()
            return error("组长用户不存在", code=BAD_REQUEST)
        leader.group_id = group.group_id
        leader.role_id = 2
        group.leader_account = leader.account
    db.session.commit()
    return success(_serialize_group(group))


@group_bp.post("/updateGroup")
@login_required
def update_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以修改小组", code=FORBIDDEN)
    data = _body()
    original = (data.get("originalGroupName") or data.get("groupName") or "").strip()
    group = Group.query.filter_by(group_name=original).first()
    if group is None:
        return error("小组不存在", code=BAD_REQUEST)

    new_name = (data.get("groupName") or "").strip() or group.group_name
    if new_name != group.group_name and Group.query.filter_by(group_name=new_name).first():
        return error("小组名称已存在", code=BAD_REQUEST)
    group.group_name = new_name

    if "reportFlag" in data:
        try:
            group.report_flag = int(data.get("reportFlag") or 0)
        except (TypeError, ValueError):
            pass

    leader_name = (data.get("leaderName") or "").strip()
    if leader_name:
        leader = User.query.filter_by(user_name=leader_name).first()
        if leader is None:
            return error("组长用户不存在", code=BAD_REQUEST)
        User.query.filter_by(group_id=group.group_id, role_id=2).update({"role_id": 1})
        leader.group_id = group.group_id
        leader.role_id = 2
        group.leader_account = leader.account
    db.session.commit()
    return success(_serialize_group(group))


@group_bp.post("/deleteGroup")
@login_required
def delete_group():
    current = load_current_user()
    if not is_admin(current):
        return error("只有总管人员可以删除小组", code=FORBIDDEN)
    data = _body()
    group = Group.query.filter_by(group_name=data.get("groupName")).first()
    if group is None:
        return error("小组不存在", code=BAD_REQUEST)
    User.query.filter_by(group_id=group.group_id).update(
        {"group_id": None, "role_id": 1}
    )
    db.session.delete(group)
    db.session.commit()
    return success(None)


@group_bp.post("/download")
@login_required
def download_groups():
    headers = ["小组名称", "组长", "成员数", "需要日报"]
    groups = Group.query.order_by(Group.group_id.asc()).all()
    rows = []
    for group in groups:
        leader = User.query.filter_by(account=group.leader_account).first()
        rows.append(
            [
                group.group_name,
                leader.user_name if leader else "",
                User.query.filter_by(group_id=group.group_id).count(),
                "是" if group.report_flag else "否",
            ]
        )
    buf = build_workbook("小组统计", headers, rows)
    return excel_response(buf, "小组统计报表.xlsx")