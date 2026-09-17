"""首页提醒模块：/api/homeReminder/*"""
from flask import Blueprint, request

from app.services import reminder_service
from app.utils.auth import load_current_user, login_required
from app.utils.response import BAD_REQUEST, error, success

home_reminder_bp = Blueprint("home_reminder", __name__, url_prefix="/api/homeReminder")


def _body():
    return request.get_json(silent=True) or {}


@home_reminder_bp.post("/queryActive")
@login_required
def query_active():
    current = load_current_user()
    return success(reminder_service.active_reminders(current.account))


@home_reminder_bp.post("/acknowledge")
@login_required
def acknowledge():
    data = _body()
    reminder_type = data.get("reminderType")
    if not reminder_type:
        return error("缺少提醒类型", code=BAD_REQUEST)
    current = load_current_user()
    reminder_service.acknowledge(current.account, reminder_type)
    return success(None)