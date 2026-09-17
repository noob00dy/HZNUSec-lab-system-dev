"""系统配置模块：/api/systemConfig/*"""
from flask import Blueprint, request

from app.extensions import db
from app.models import SystemConfig
from app.utils.auth import is_admin, load_current_user, login_required
from app.utils.response import BAD_REQUEST, FORBIDDEN, error, success

system_config_bp = Blueprint("system_config", __name__, url_prefix="/api/systemConfig")


def _body():
    return request.get_json(silent=True) or {}


def _require_admin():
    current = load_current_user()
    if current is None:
        return error("请先登录", code="399")
    if not is_admin(current):
        return error("只有总管人员可以修改系统配置", code=FORBIDDEN)
    return None


@system_config_bp.post("/queryReportType")
def query_report_type():
    value = SystemConfig.get_value(SystemConfig.REPORT_TYPE, "0")
    return success(msg=value)


@system_config_bp.post("/updateReportType")
@login_required
def update_report_type():
    denied = _require_admin()
    if denied:
        return denied
    data = _body()
    value = str(data.get("configValue", "0"))
    if value not in {"0", "1", "2"}:
        return error("配置值非法", code=BAD_REQUEST)
    SystemConfig.set_value(
        SystemConfig.REPORT_TYPE, value, "报告发送方式：0 不发送 / 1 日报 / 2 周报"
    )
    db.session.commit()
    return success(None)


@system_config_bp.post("/queryIsSkipHolidays")
def query_skip_holidays():
    value = SystemConfig.get_value(SystemConfig.SKIP_HOLIDAYS, "0")
    return success(msg=value)


@system_config_bp.post("/updateIsSkipHolidays")
@login_required
def update_skip_holidays():
    denied = _require_admin()
    if denied:
        return denied
    data = _body()
    value = str(data.get("configValue", "0"))
    if value not in {"0", "1"}:
        return error("配置值非法", code=BAD_REQUEST)
    SystemConfig.set_value(
        SystemConfig.SKIP_HOLIDAYS, value, "日报/签到是否跳过节假日：0 否 / 1 是"
    )
    db.session.commit()
    return success(None)