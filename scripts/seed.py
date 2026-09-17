"""初始化基础数据：角色、管理员、示例小组、系统配置。

用法：
    flask --app run.py seed
或：
    python -m scripts.seed
"""
from datetime import date

from app.extensions import db
from app.models import Group, Role, SystemConfig, User
from app.utils.auth import hash_password

ROLES = [
    (1, "user", "普通用户"),
    (2, "groupLeader", "组长"),
    (3, "allLeader", "老师/总管人员"),
]

DEFAULT_GROUPS = ["研究一组", "研究二组", "实战攻防组"]

DEFAULT_CONFIGS = [
    (SystemConfig.REPORT_TYPE, "1", "报告发送方式：0 不发送 / 1 日报 / 2 周报"),
    (SystemConfig.SKIP_HOLIDAYS, "1", "日报/签到是否跳过节假日：0 否 / 1 是"),
]


def run_seed():
    # 角色
    for role_id, name, description in ROLES:
        role = Role.query.filter_by(role_id=role_id).first()
        if role is None:
            role = Role(role_id=role_id, role_name=name, description=description)
            db.session.add(role)
        else:
            role.role_name = name
            role.description = description

    # 小组
    for group_name in DEFAULT_GROUPS:
        if not Group.query.filter_by(group_name=group_name).first():
            db.session.add(Group(group_name=group_name, report_flag=1))
    db.session.flush()

    # 管理员
    admin = User.query.filter_by(account="admin").first()
    if admin is None:
        admin = User(
            account="admin",
            password_hash=hash_password("admin123"),
            user_name="系统管理员",
            role_id=3,
            email="admin@example.com",
            input_date=date.today(),
        )
        db.session.add(admin)

    # 示例普通用户
    demo = User.query.filter_by(account="demo").first()
    if demo is None:
        first_group = Group.query.filter_by(group_name=DEFAULT_GROUPS[0]).first()
        demo = User(
            account="demo",
            password_hash=hash_password("demo123"),
            user_name="演示用户",
            role_id=1,
            group_id=first_group.group_id if first_group else None,
            report_flag=1,
            input_date=date.today(),
        )
        db.session.add(demo)

    # 系统配置
    for key, value, description in DEFAULT_CONFIGS:
        if SystemConfig.query.filter_by(config_key=key).first() is None:
            db.session.add(
                SystemConfig(config_key=key, config_value=value, description=description)
            )

    db.session.commit()
    print("初始化完成：")
    print("  管理员账号 admin / admin123")
    print("  普通用户 demo  / demo123")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run_seed()