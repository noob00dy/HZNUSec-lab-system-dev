"""蓝图统一注册。"""
from app.api.achievement import achievement_bp
from app.api.agent import agent_bp
from app.api.auth import auth_bp
from app.api.course import course_bp
from app.api.email_group import email_group_bp
from app.api.file_record import file_record_bp
from app.api.group import group_bp
from app.api.home_reminder import home_reminder_bp
from app.api.leave import leave_bp
from app.api.meeting import meeting_bp, user_meeting_bp
from app.api.meeting_signin import meeting_signin_bp
from app.api.record import record_bp
from app.api.report import report_bp
from app.api.sign_duration import sign_duration_bp
from app.api.system_config import system_config_bp
from app.api.user import user_bp

ALL_BLUEPRINTS = (
    auth_bp,
    user_bp,
    group_bp,
    record_bp,
    sign_duration_bp,
    report_bp,
    meeting_bp,
    user_meeting_bp,
    meeting_signin_bp,
    leave_bp,
    file_record_bp,
    system_config_bp,
    home_reminder_bp,
    email_group_bp,
    course_bp,
    achievement_bp,
    agent_bp,
)


def register_blueprints(app):
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)


__all__ = ["register_blueprints", "ALL_BLUEPRINTS"]