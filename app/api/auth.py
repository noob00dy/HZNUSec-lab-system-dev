"""认证模块：/api/login/*"""
from flask import request

from app.extensions import db
from app.models import Group, Role, User
from app.utils.auth import (
    generate_token,
    hash_password,
    load_current_user,
    login_required,
    verify_password,
)
from app.utils.response import BAD_REQUEST, error, success

from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/api/login")


def _payload():
    return request.get_json(silent=True) or request.form.to_dict() or {}


@auth_bp.post("/loginIn")
def login_in():
    data = _payload()
    account = (data.get("account") or "").strip()
    password = data.get("password") or ""
    if not account or not password:
        return error("账号和密码不能为空", code=BAD_REQUEST)

    user = User.query.filter_by(account=account).first()
    if user is None or not verify_password(user.password_hash, password):
        return error("账号或密码错误", code=BAD_REQUEST)
    if not user.is_active:
        return error("账号已被禁用，请联系管理员", code=BAD_REQUEST)

    token = generate_token(user)
    return success(
        {
            "userName": user.user_name,
            "role": user.role_name,
            "token": token,
            "account": user.account,
        }
    )


@auth_bp.post("/register")
def register():
    data = _payload()
    account = (data.get("account") or "").strip()
    password = data.get("password") or ""
    user_name = (data.get("userName") or "").strip()
    if not account or not password or not user_name:
        return error("账号、密码、姓名不能为空", code=BAD_REQUEST)
    if User.query.filter_by(account=account).first():
        return error("该账号已存在", code=BAD_REQUEST)

    group_name = (data.get("groupName") or "").strip()
    group = Group.query.filter_by(group_name=group_name).first() if group_name else None

    sex = data.get("sex", 0)
    try:
        sex = int(sex)
    except (TypeError, ValueError):
        sex = 0

    user = User(
        account=account,
        password_hash=hash_password(password),
        user_name=user_name,
        sex=sex,
        phone=data.get("phone"),
        grade=data.get("grade"),
        email=data.get("email"),
        stu_number=data.get("stuNumber"),
        class_name=data.get("className"),
        group_id=group.group_id if group else None,
        role_id=1,
    )
    db.session.add(user)
    db.session.commit()
    return success({"account": user.account})


@auth_bp.get("/info")
def login_info():
    """GET /api/login/info，前端路由守卫用于校验登录态。"""
    user = load_current_user()
    if user is None:
        # 与旧系统一致：未登录返回 399，由前端跳转登录页
        return error("登录状态已失效", code="399")
    return success(
        {
            "user": {"account": user.account, "role": user.role_name},
            "permissions": [],
            "menus": [],
        }
    )


@auth_bp.post("/logout")
def logout():
    # JWT 无状态，前端清除本地 token 即可；保留接口以便扩展黑名单
    return success(None)