"""鉴权：JWT 签发/校验，兼容旧系统 satoken 头。"""
from datetime import datetime
from functools import wraps

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import User
from app.utils.response import UNAUTHORIZED, FORBIDDEN, error


def hash_password(raw):
    return generate_password_hash(raw or "")


def verify_password(password_hash, raw):
    try:
        return check_password_hash(password_hash, raw or "")
    except Exception:
        return False


def generate_token(user):
    now = datetime.utcnow()
    payload = {
        "sub": str(user.account),
        "uid": user.id,
        "role": user.role_name,
        "iat": now,
        "exp": now + current_app.config["JWT_EXPIRES"],
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def _extract_token():
    token = request.headers.get("satoken") or request.headers.get("Satoken")
    if token:
        return token.strip()
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.args.get("token")


def decode_token(token):
    try:
        return jwt.decode(
            token,
            current_app.config["JWT_SECRET"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
    except Exception:
        return None


def load_current_user():
    """解析当前登录用户，缓存到 flask.g。"""
    if getattr(g, "current_user", None) is not None:
        return g.current_user
    g.current_user = None
    token = _extract_token()
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = User.query.filter_by(account=payload.get("sub")).first()
    if user and user.is_active:
        g.current_user = user
        g.jwt_payload = payload
        return user
    return None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if load_current_user() is None:
            return error("请先登录", code=UNAUTHORIZED)
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    """限定角色访问，roles 传角色名（user/groupLeader/allLeader）。"""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = load_current_user()
            if user is None:
                return error("请先登录", code=UNAUTHORIZED)
            if user.role_name not in roles:
                return error("没有操作权限", code=FORBIDDEN)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def is_admin(user=None):
    user = user or load_current_user()
    return bool(user and user.role_name == "allLeader")


def can_manage_group(user, group_id):
    """allLeader 可管理全部；groupLeader 仅能管理自己所在小组。"""
    if not user:
        return False
    if user.role_name == "allLeader":
        return True
    return user.role_name == "groupLeader" and user.group_id == group_id