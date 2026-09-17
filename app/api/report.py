"""日报模块：/api/report/*"""
import json

from flask import Blueprint, current_app, request

from app.extensions import db
from app.models import Group, Report, User
from app.services import report_service
from app.utils.excel import build_workbook, excel_response
from app.utils.files import save_upload
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, error, success
from app.utils.timeutil import parse_date

report_bp = Blueprint("report", __name__, url_prefix="/api/report")


def _body():
    return request.get_json(silent=True) or {}


@report_bp.post("/hasSubmittedToday")
def has_submitted_today():
    data = _body()
    account = data.get("account")
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)
    return success(report_service.has_submitted(account))


@report_bp.post("/reportSubmit")
def report_submit():
    raw = request.form.get("reportJson")
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
    else:
        data = _body()
    account = data.get("account")
    if not account:
        return error("缺少账号参数", code=BAD_REQUEST)

    report = report_service.submit(
        account,
        data.get("workContent", ""),
        data.get("problems", ""),
        data.get("plan", ""),
    )

    files = request.files.getlist("files")
    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue
        record, _ = save_upload(
            file_storage,
            subdir="reports",
            upload_folder=current_app.config["UPLOAD_FOLDER"],
            account=account,
            user_name=report.user_name,
            source_type=1,
            related_id=report.id,
        )
        db.session.add(record)
    db.session.commit()
    return success({"id": report.id})


def _query(data):
    query = Report.query
    user_name = (data.get("userName") or "").strip()
    group_name = (data.get("groupName") or "").strip()
    account = data.get("account")
    if account:
        query = query.filter(Report.account == account)
    if user_name:
        query = query.filter(Report.user_name.like(f"%{user_name}%"))
    if group_name:
        group = Group.query.filter_by(group_name=group_name).first()
        query = query.filter(
            Report.group_id == (group.group_id if group else -1)
        )
    start = parse_date(data.get("startDate"))
    end = parse_date(data.get("endDate"))
    if start:
        query = query.filter(Report.report_date >= start)
    if end:
        query = query.filter(Report.report_date <= end)
    return query


def _serialize(report, group_names):
    data = report.to_dict()
    data["groupName"] = group_names.get(report.group_id, "")
    return data


@report_bp.post("/queryReportByPage")
def query_report_by_page():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = _query(data).order_by(Report.report_date.desc(), Report.id.desc())
    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    items, total = paginate(query, page, size, lambda r: _serialize(r, group_names))
    return success(
        {
            "reportList": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@report_bp.post("/download")
def download_reports():
    data = _body()
    group_names = {g.group_id: g.group_name for g in Group.query.all()}
    reports = _query(data).order_by(Report.report_date.desc()).all()
    headers = ["姓名", "小组", "日期", "工作内容", "问题", "计划"]
    rows = [
        [
            r.user_name,
            group_names.get(r.group_id, ""),
            r.report_date.strftime("%Y-%m-%d"),
            r.work_content,
            r.problems,
            r.plan,
        ]
        for r in reports
    ]
    buf = build_workbook("日报明细", headers, rows)
    return excel_response(buf, "日报明细.xlsx")


@report_bp.post("/downloadSummary")
def download_summary():
    data = _body()
    period_type = (data.get("periodType") or "WEEK").upper()
    headers, rows = report_service.group_report_summary(
        period_type,
        data.get("period"),
        data.get("userName"),
        data.get("groupName"),
    )
    filename = "日报周汇总.xlsx" if period_type == "WEEK" else "日报月汇总.xlsx"
    buf = build_workbook("日报汇总", headers, rows)
    return excel_response(buf, filename)