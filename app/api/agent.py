"""智能助手模块：/api/agent/ask"""
from flask import Blueprint, request

from app.services.summary_service import ask_agent
from app.utils.response import success

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")


@agent_bp.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    answer = ask_agent(data.get("prompt"), data.get("question"))
    return success(msg=answer)