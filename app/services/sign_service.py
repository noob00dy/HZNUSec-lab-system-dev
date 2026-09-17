"""签到业务逻辑。

规则（与旧系统一致）：
- 每天可签到一次、签退一次；
- 未签退的记录在跨天时自动以当天 23:59:59 结束；
- 签到时长按天聚合，单位小时，保留 1 位小数。
"""
from datetime import datetime, time, timedelta

from app.extensions import db
from app.models import SignDuration, SignRecord, User
from app.utils.timeutil import today


def _close_stale_records(account, before_date):
    """把 before_date 之前仍未签退的记录补为当天 23:59:59。"""
    stale = (
        SignRecord.query.filter(
            SignRecord.account == account,
            SignRecord.end_time.is_(None),
            SignRecord.report_date < before_date,
        )
        .all()
    )
    for rec in stale:
        rec.end_time = datetime.combine(rec.report_date, time(23, 59, 59))
        _recompute(account, rec.report_date)
    return stale


def current_status(account):
    """1 = 未签到（可签到）；2 = 已签到（可签退）。"""
    open_record = (
        SignRecord.query.filter_by(account=account, end_time=None)
        .order_by(SignRecord.start_time.desc())
        .first()
    )
    return 2 if open_record else 1


def check_in(account):
    day = today()
    _close_stale_records(account, day)
    open_record = SignRecord.query.filter_by(account=account, end_time=None).first()
    if open_record:
        return False, "今日已签到，请勿重复签到"
    user = User.query.filter_by(account=account).first()
    record = SignRecord(
        account=account,
        report_date=day,
        start_time=datetime.now(),
    )
    db.session.add(record)
    db.session.commit()
    _recompute(account, day, group_id=user.group_id if user else None)
    return True, "签到成功"


def check_out(account):
    open_record = (
        SignRecord.query.filter_by(account=account, end_time=None)
        .order_by(SignRecord.start_time.desc())
        .first()
    )
    if not open_record:
        return False, "尚未签到，无法签退"
    open_record.end_time = datetime.now()
    db.session.commit()
    user = User.query.filter_by(account=account).first()
    _recompute(account, open_record.report_date, group_id=user.group_id if user else None)
    return True, "签退成功"


def _recompute(account, report_date, group_id=None):
    records = SignRecord.query.filter_by(account=account, report_date=report_date).all()
    total_seconds = 0.0
    for rec in records:
        end = rec.end_time or datetime.now()
        delta = (end - rec.start_time).total_seconds()
        if delta > 0:
            total_seconds += delta
    hours = round(total_seconds / 3600.0, 1)
    row = SignDuration.query.filter_by(account=account, report_date=report_date).first()
    if row is None:
        row = SignDuration(account=account, report_date=report_date, group_id=group_id)
        db.session.add(row)
    row.sign_duration = hours
    if group_id is not None:
        row.group_id = group_id
    db.session.commit()
    return row


def week_durations(account, days=7):
    """返回指定用户最近/当周每日签到时长。"""
    from app.utils.timeutil import week_range

    monday, sunday = week_range()
    rows = {
        r.report_date: r.sign_duration
        for r in SignDuration.query.filter(
            SignDuration.account == account,
            SignDuration.report_date >= monday,
            SignDuration.report_date <= sunday,
        ).all()
    }
    result = []
    cur = monday
    while cur <= sunday:
        result.append(
            {
                "reportDate": cur.strftime("%Y-%m-%d"),
                "signDuration": round(rows.get(cur, 0.0) or 0.0, 1),
            }
        )
        cur += timedelta(days=1)
    return result


def multi_user_week(accounts):
    """多人本周签到曲线，用于 /signDuration/queryWeek。"""
    return [
        {"userName": _name_of(acc), "weekList": week_durations(acc)}
        for acc in accounts
    ]


def group_totals(start_date=None, end_date=None):
    """按小组聚合签到时长，用于「各组签到时长分布」图。"""
    from app.models import Group

    query = db.session.query(
        SignDuration.group_id, db.func.sum(SignDuration.sign_duration)
    )
    if start_date:
        query = query.filter(SignDuration.report_date >= start_date)
    if end_date:
        query = query.filter(SignDuration.report_date <= end_date)
    query = query.group_by(SignDuration.group_id)

    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    result = []
    for group_id, total in query.all():
        result.append(
            {
                "groupName": group_names.get(group_id, "未分组"),
                "signDuration": round(float(total or 0), 1),
            }
        )
    return result


def _name_of(account):
    user = User.query.filter_by(account=account).first()
    return user.user_name if user else account