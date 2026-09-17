"""文件上传辅助。"""
import os
import uuid
from datetime import datetime

from werkzeug.utils import secure_filename

from app.models import FileRecord


def save_upload(file_storage, subdir, upload_folder, account=None, user_name=None,
                source_type=3, related_id=None, uploaded_by=None):
    """保存上传文件并写入 FileRecord。返回 FileRecord。"""
    original = file_storage.filename or "unnamed"
    ext = os.path.splitext(original)[1]
    stored_name = uuid.uuid4().hex + ext
    folder = os.path.join(upload_folder, subdir, datetime.now().strftime("%Y/%m"))
    os.makedirs(folder, exist_ok=True)
    abs_path = os.path.join(folder, stored_name)
    file_storage.save(abs_path)

    size = os.path.getsize(abs_path)
    rel_path = os.path.join("/data/files", subdir,
                            datetime.now().strftime("%Y/%m"), stored_name).replace("\\", "/")
    record = FileRecord(
        file_name=secure_filename(original) or original,
        file_path=rel_path,
        file_size=size,
        uploaded_by=uploaded_by or account,
        user_name=user_name,
        account=account,
        uploaded_at=datetime.now(),
        file_type=FileRecord.detect_type(original),
        source_type=source_type,
        related_id=related_id,
    )
    return record, abs_path


def resolve_abs_path(record, upload_folder):
    """将 FileRecord.file_path 映射为磁盘绝对路径。"""
    name = os.path.basename(record.file_path)
    # file_path 形如 /data/files/<subdir>/YYYY/MM/name
    parts = [p for p in record.file_path.split("/") if p]
    if parts and parts[0] == "data" and len(parts) > 2 and parts[1] == "files":
        relative = os.path.join(*parts[2:])
    else:
        relative = name
    return os.path.join(upload_folder, relative)