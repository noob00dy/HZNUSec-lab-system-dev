"""首页提醒业务逻辑。

旧系统首页会展示两类提醒：
- REPORT：超过 60 小时未提交日报；
- SIGN_DURATION：本周签到时长不足 24 小时。
用户确认（acknowledge）后按周期不再展示。
"""
from datetime import datetime

from app.extensions import db
from app.models import Group, HomeReminder, Report, SignDuration, User

REPORT_REMINDER = "REPORT"
SIGN_DURATION_REMINDER = "SIGN_DURATION"

REPORT_THRESHOLD_HOURS = 60
WEEK_DURATION_THRESHOLD = 24.0


def _report_cycle_key(user):
    latest = (
        Report.query.filter_by(account=user.account)
        .order_by(Report.report_date.desc())
        .first()
    )
    stamp = latest.report_date.strftime("%Y%m%d") if latest else "none"
    return f"REPORT:{stamp}"


def _sign_cycle_key():
    iso = datetime.now().isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _build_reminders(user):
    reminders = []
    group = user.group if user.group_id else None
    need_report = bool(user.report_flag) or (group and group.report_flag)
    if need_report:
        latest = (
            Report.query.filter_by(account=user.account)
            .order_by(Report.report_date.desc())
            .first()
        )
        overdue = True
        if latest is not None:
            elapsed = datetime.now() - datetime.combine(
                latest.report_date, datetime.max.time()
            )
            overdue = elapsed.total_seconds() > REPORT_THRESHOLD_HOURS * 3600
        if overdue:
            reminders.append(
                {
                    "reminderType": REPORT_REMINDER,
                    "title": "日报提交提醒",
                    "message": f"距离上次日报提交已超过 {REPORT_THRESHOLD_HOURS} 小时，请及时提交。",
                    "cycleKey": _report_cycle_key(user),
                }
            )

    week_total = _week_total(user.account)
    if week_total < WEEK_DURATION_THRESHOLD:
        reminders.append(
            {
                "reminderType": SIGN_DURATION_REMINDER,
                "title": "签到时长提醒",
                "message": f"本周累计签到 {week_total} 小时，不足 {int(WEEK_DURATION_THRESHOLD)} 小时，请注意签到时间。",
                "cycleKey": _sign_cycle_key(),
            }
        )
    return reminders


def _week_total(account):
    from app.utils.timeutil import week_range

    monday, sunday = week_range()
    total = (
        db.session.query(db.func.sum(SignDuration.sign_duration))
        .filter(
            SignDuration.account == account,
            SignDuration.report_date >= monday,
            SignDuration.report_date <= sunday,
        )
        .scalar()
    )
    return round(float(total or 0.0), 1)


def active_reminders(account):
    user = User.query.filter_by(account=account).first()
    if not user:
        return []
    candidates = _build_reminders(user)
    acknowledged = {
        (r.reminder_type, r.cycle_key)
        for r in HomeReminder.query.filter_by(
            account=account, is_acknowledged=True
        ).all()
    }
    result = []
    for item in candidates:
        if (item["reminderType"], item["cycleKey"]) in acknowledged:
            continue
        # 落库，便于统计
        persist_reminder(account, item)
        result.append(item)
    return result


def persist_reminder(account, item):
    row = HomeReminder.query.filter_by(
        account=account,
        reminder_type=item["reminderType"],
        cycle_key=item["cycleKey"],
    ).first()
    if row is None:
        row = HomeReminder(
            account=account,
            reminder_type=item["reminderType"],
            cycle_key=item["cycleKey"],
        )
        db.session.add(row)
    row.title = item.get("title", "")
    row.message = item.get("message", "")
    db.session.commit()
    return row


def acknowledge(account, reminder_type):
    user = User.query.filter_by(account=account).first()
    if not user:
        return False
    cycle_key = None
    for item in _build_reminders(user):
        if item["reminderType"] == reminder_type:
            cycle_key = item["cycleKey"]
            persist_reminder(account, item)
    if cycle_key is None:
        # 没有活跃提醒时也允许确认，记录一个当前周期为空键
        cycle_key = _report_cycle_key(user) if reminder_type == REPORT_REMINDER else _sign_cycle_key()
    row = HomeReminder.query.filter_by(
        account=account, reminder_type=reminder_type, cycle_key=cycle_key
    ).first()
    if row is None:
        row = HomeReminder(
            account=account,
            reminder_type=reminder_type,
            cycle_key=cycle_key,
        )
        db.session.add(row)
    row.is_acknowledged = True
    db.session.commit()
    return True