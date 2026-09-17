"""日期/时间工具。"""
from calendar import monthrange
from datetime import date, datetime, timedelta

DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def today():
    return date.today()


def now():
    return datetime.now()


def parse_date(value, default=None):
    if not value:
        return default
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    value = str(value).strip()
    for pattern in (DATE_FMT, DATETIME_FMT, "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return default


def parse_datetime(value, default=None):
    if not value:
        return default
    if isinstance(value, datetime):
        return value
    value = str(value).strip()
    for pattern in (DATETIME_FMT, DATE_FMT, "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return default


def week_range(anchor=None):
    """返回 anchor 所在周的周一~周日。"""
    anchor = parse_date(anchor, date.today())
    monday = anchor - timedelta(days=anchor.weekday())
    return monday, monday + timedelta(days=6)


def month_range(anchor=None):
    anchor = parse_date(anchor, date.today())
    start = anchor.replace(day=1)
    end = anchor.replace(day=monthrange(anchor.year, anchor.month)[1])
    return start, end


def period_range(period_type, period=None):
    """periodType=WEEK/MONTH 的时间区间。"""
    if (period_type or "").upper() == "MONTH":
        return month_range(period)
    return week_range(period)


def is_holiday(day):
    """法定节假日判断（周末近似，可接入节假日表扩展）。"""
    return day.weekday() >= 5


def date_iter(start, end):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)