import os

from app.extensions import db
from app.models.base import TimestampMixin, fmt

# 文件来源类型
SOURCE_REPORT = 1    # 日报周报
SOURCE_MEETING = 2   # 会议共享
SOURCE_PROJECT = 3   # 项目文件

SOURCE_LABELS = {1: "日报周报", 2: "会议共享", 3: "项目文件"}


class FileRecord(db.Model, TimestampMixin):
    """文件记录。"""

    __tablename__ = "file_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.BigInteger, default=0)
    uploaded_by = db.Column(db.String(64), index=True)
    user_name = db.Column(db.String(64))
    account = db.Column(db.String(64), index=True)
    uploaded_at = db.Column(db.DateTime)
    file_type = db.Column(db.String(32), default="Unknown")
    source_type = db.Column(db.SmallInteger, default=SOURCE_PROJECT, nullable=False)
    related_id = db.Column(db.Integer, index=True)

    @staticmethod
    def detect_type(filename):
        ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
        mapping = {
            "pdf": "PDF",
            "doc": "Word",
            "docx": "Word",
            "xls": "Excel",
            "xlsx": "Excel",
            "ppt": "PPT",
            "pptx": "PPT",
            "png": "Image",
            "jpg": "Image",
            "jpeg": "Image",
            "gif": "Image",
            "zip": "Archive",
            "rar": "Archive",
            "txt": "Text",
            "md": "Text",
        }
        return mapping.get(ext, "Unknown")

    def to_dict(self):
        return {
            "id": self.id,
            "fileName": self.file_name,
            "filePath": self.file_path,
            "fileSize": self.file_size,
            "uploadedBy": self.uploaded_by,
            "userName": self.user_name,
            "uploadedAt": fmt(self.uploaded_at),
            "fileType": self.file_type,
            "sourceType": self.source_type,
            "sourceLabel": SOURCE_LABELS.get(self.source_type, "未知"),
            "relatedId": self.related_id,
        }

    def to_meeting_file(self):
        return {
            "id": self.id,
            "fileName": self.file_name,
            "fileSize": self.file_size,
            "uploadedBy": self.uploaded_by,
            "userName": self.user_name,
            "uploadedAt": fmt(self.uploaded_at),
            "fileType": self.file_type,
            "sourceType": self.source_type,
            "relatedId": self.related_id,
        }