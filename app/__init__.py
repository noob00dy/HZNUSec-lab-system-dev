"""实验室智能管理系统 —— Flask 应用工厂。"""
import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.api import register_blueprints
from app.config import get_config
from app.extensions import db


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # 中文直接输出，不转义；保持字段顺序
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    _ensure_dirs(app)

    db.init_app(app)
    _init_cors(app)

    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)

    with app.app_context():
        # 首次启动自动建表，方便开发；生产建议使用迁移工具
        from app import models  # noqa: F401

        db.create_all()

    @app.get("/api/health")
    def health():
        return jsonify({"code": "200", "data": {"status": "ok"}})

    return app


def _ensure_dirs(app):
    upload = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload, exist_ok=True)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
        os.makedirs(instance_dir, exist_ok=True)


def _init_cors(app):
    origins = app.config.get("CORS_ORIGINS", "*")
    if isinstance(origins, str):
        origins = origins if origins == "*" else [o.strip() for o in origins.split(",")]
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "satoken"],
        expose_headers=["Content-Disposition"],
    )


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"code": "404", "message": "接口不存在"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"code": "405", "message": "请求方法不被允许"}), 405

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"code": "413", "message": "上传文件过大"}), 413

    @app.errorhandler(Exception)
    def server_error(exc):
        if isinstance(exc, HTTPException):
            return jsonify({"code": str(exc.code), "message": exc.description}), exc.code
        app.logger.exception("未处理异常: %s", exc)
        return jsonify({"code": "500", "message": "服务器内部错误"}), 500


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """创建所有数据表。"""
        from app import models  # noqa: F401

        db.create_all()
        print("数据表创建完成。")

    @app.cli.command("seed")
    def seed():
        """初始化角色、管理员与示例小组。"""
        from scripts.seed import run_seed

        run_seed()