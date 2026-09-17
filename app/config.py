import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """全局配置，全部可通过环境变量覆盖。"""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET = os.getenv("JWT_SECRET") or SECRET_KEY
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "24")))

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "lab.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 3600}

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER") or os.path.join(BASE_DIR, "data", "files")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # 角色常量（与旧系统保持一致）
    ROLE_USER = 1
    ROLE_GROUP_LEADER = 2
    ROLE_ALL_LEADER = 3

    ROLE_NAMES = {
        1: ("user", "普通用户"),
        2: ("groupLeader", "组长"),
        3: ("allLeader", "老师/总管人员"),
    }

    @property
    def cors_origins(self):
        raw = (self.CORS_ORIGINS or "*").strip()
        if raw == "*":
            return "*"
        return [o.strip() for o in raw.split(",") if o.strip()]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name=None):
    return CONFIG_MAP.get(name or os.getenv("FLASK_ENV", "default"), DevelopmentConfig)