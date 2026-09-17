"""日报业务逻辑。"""
from app.extensions import db
from app.models import Group, Report, User
from app.utils.timeutil import today


def has_submitted(account, day=None):
    day = day or today()
    return (
        Report.query.filter_by(account=account, report_date=day).first() is not None
    )


def submit(account, work_content, problems, plan, day=None, files=None):
    """提交/更新日报（同一天重复提交则覆盖）。"""
    day = day or today()
    user = User.query.filter_by(account=account).first()
    report = Report.query.filter_by(account=account, report_date=day).first()
    if report is None:
        report = Report(account=account, report_date=day)
        db.session.add(report)
    report.user_name = user.user_name if user else account
    report.group_id = user.group_id if user else None
    report.work_content = work_content or ""
    report.problems = problems or ""
    report.plan = plan or ""
    db.session.commit()
    return report


def missing_report_users(hours=60):
    """返回超过指定小时数未提交日报的用户，用于首页提醒。"""
    from datetime import datetime, timedelta

    deadline = datetime.now() - timedelta(hours=hours)
    users = User.query.filter(User.is_active.is_(True)).all()
    result = []
    for user in users:
        latest = (
            Report.query.filter_by(account=user.account)
            .order_by(Report.report_date.desc())
            .first()
        )
        if latest is None or datetime.combine(latest.report_date, datetime.min.time()) < deadline:
            result.append(user)
    return result


def group_report_summary(period_type, period, user_name=None, group_name=None):
    """按周/月汇总日报，返回 (headers, rows)。"""
    from app.utils.timeutil import period_range

    start, end = period_range(period_type, period)
    query = Report.query.filter(Report.report_date >= start, Report.report_date <= end)
    if user_name:
        query = query.filter(Report.user_name.like(f"%{user_name}%"))
    if group_name:
        group = Group.query.filter_by(group_name=group_name).first()
        if group:
            query = query.filter(Report.group_id == group.group_id)
    reports = query.order_by(Report.report_date.asc()).all()

    headers = ["姓名", "小组", "日期", "工作内容", "问题", "计划"]
    group_map = {g.group_id: g.group_name for g in Group.query.all()}
    rows = [
        [
            r.user_name,
            group_map.get(r.group_id, ""),
            r.report_date.strftime("%Y-%m-%d"),
            r.work_content,
            r.problems,
            r.plan,
        ]
        for r in reports
    ]
    return headers, rows