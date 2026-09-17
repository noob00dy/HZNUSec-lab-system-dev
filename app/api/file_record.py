"""文件模块：/api/fileRecord/*"""
import os

from flask import Blueprint, current_app, request, send_file

from app.models import FileRecord
from app.utils.pagination import normalize_page, paginate
from app.utils.response import BAD_REQUEST, NOT_FOUND, error, success
from app.utils.timeutil import parse_date

file_record_bp = Blueprint("file_record", __name__, url_prefix="/api/fileRecord")


def _body():
    return request.get_json(silent=True) or {}


@file_record_bp.post("/queryFileRecordByPage")
def query_by_page():
    data = _body()
    page, size = normalize_page(data.get("page"), data.get("size"))
    query = FileRecord.query
    user_name = (data.get("userName") or "").strip()
    if user_name:
        query = query.filter(FileRecord.user_name.like(f"%{user_name}%"))
    file_name = (data.get("fileName") or "").strip()
    if file_name:
        query = query.filter(FileRecord.file_name.like(f"%{file_name}%"))
    source_type = data.get("sourceType")
    if source_type not in (None, "", "undefined"):
        try:
            query = query.filter(FileRecord.source_type == int(source_type))
        except (TypeError, ValueError):
            pass
    report_date = parse_date(data.get("reportDate"))
    if report_date:
        from datetime import datetime, time

        query = query.filter(FileRecord.uploaded_at >= datetime.combine(report_date, time.min))
        query = query.filter(FileRecord.uploaded_at <= datetime.combine(report_date, time.max))

    query = query.order_by(FileRecord.id.desc())
    items, total = paginate(query, page, size, lambda f: f.to_dict())
    return success(
        {
            "fileList": items,
            "dataCount": total,
            "page": page,
            "size": size,
            "pageCount": (total + size - 1) // size,
        }
    )


@file_record_bp.post("/downloadFile")
def download_file():
    data = _body()
    record = FileRecord.query.get(data.get("id"))
    if record is None:
        return error("文件不存在", code=NOT_FOUND)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    parts = [p for p in record.file_path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "data" and parts[1] == "files":
        relative = os.path.join(*parts[2:])
    else:
        relative = os.path.basename(record.file_path)
    abs_path = os.path.join(upload_folder, relative)
    if not os.path.exists(abs_path):
        return error("文件已丢失", code=NOT_FOUND)
    return send_file(abs_path, as_attachment=True, download_name=record.file_name)