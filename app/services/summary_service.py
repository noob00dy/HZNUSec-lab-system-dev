"""AI / 文本总结服务。

- 会议纪要生成（/meeting/getMeetingMinutes）
- 个人总结生成（/api/user/generatePersonalSummary）
- 智能建议问答（/agent/ask）

配置 AI_API_BASE / AI_API_KEY / AI_MODEL 后接入大模型；
未配置时使用本地规则生成，保证功能可用。
"""
import os

import requests as http

from app.extensions import db
from app.models import Meeting, MeetingMember, Report, SignDuration, User

AI_API_BASE = os.getenv("AI_API_BASE", "").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")


def _call_llm(system_prompt, user_prompt, timeout=30):
    """调用 OpenAI 兼容的 chat/completions 接口。未配置则返回 None。"""
    if not (AI_API_BASE and AI_API_KEY and AI_MODEL):
        return None
    try:
        resp = http.post(
            f"{AI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def generate_meeting_minutes(meeting: Meeting):
    attendees = MeetingMember.query.filter_by(meeting_id=meeting.meeting_id).all()
    checked = [m.user_name or m.account for m in attendees if m.checked_in]
    absent = [m.user_name or m.account for m in attendees if not m.checked_in and m.status != 2]
    leave = [m.user_name or m.account for m in attendees if m.status == 2]

    prompt = (
        f"会议名称：{meeting.meeting_name}\n"
        f"会议时间：{meeting.start_at}\n"
        f"会议地点：{meeting.location}\n"
        f"会议说明：{meeting.description}\n"
        f"应到人数：{len(attendees)}，实到：{len(checked)}，请假：{len(leave)}，缺席：{len(absent)}\n"
        f"会议关键字：{meeting.keyword or '无'}\n"
        "请根据以上信息生成一段简洁的会议纪要，包含会议要点与出勤情况。"
    )
    content = _call_llm("你是一名实验室会议纪要助手。", prompt)
    if not content:
        content = (
            f"【{meeting.meeting_name}】会议纪要\n"
            f"时间：{meeting.start_at:%Y-%m-%d %H:%M}  地点：{meeting.location or '未填写'}\n"
            f"会议说明：{meeting.description or '无'}\n"
            f"关键字：{meeting.keyword or '无'}\n"
            f"出勤：应到 {len(attendees)} 人，实到 {len(checked)} 人，请假 {len(leave)} 人，缺席 {len(absent)} 人。\n"
            f"缺席名单：{('、'.join(absent)) or '无'}"
        )
    meeting.summary = content
    db.session.commit()
    return content


def generate_personal_summary(account):
    user = User.query.filter_by(account=account).first()
    if not user:
        return None
    reports = (
        Report.query.filter_by(account=account)
        .order_by(Report.report_date.desc())
        .limit(20)
        .all()
    )
    total = (
        db.session.query(db.func.sum(SignDuration.sign_duration))
        .filter(SignDuration.account == account)
        .scalar()
        or 0.0
    )
    works = "\n".join(f"- {r.report_date}: {r.work_content}" for r in reports)
    prompt = (
        f"姓名：{user.user_name}\n累计签到时长：{round(float(total), 1)} 小时\n"
        f"近期工作记录：\n{works}\n请生成一份 200 字以内的个人阶段性总结与改进建议。"
    )
    content = _call_llm("你是一名实验室个人成长分析助手。", prompt)
    if not content:
        content = (
            f"{user.user_name} 同学累计签到 {round(float(total), 1)} 小时，"
            f"近期提交日报 {len(reports)} 篇。"
            "建议保持稳定的签到节奏，并在日报中更具体地记录问题与解决过程。"
        )
    return content


def ask_agent(prompt, question):
    content = _call_llm(
        prompt or "你是实验室智能管理助手，请用中文回答。",
        question or "",
    )
    if not content:
        content = (
            f"已收到你的问题：{question}\n"
            "当前未配置 AI 服务（AI_API_BASE/AI_API_KEY/AI_MODEL），"
            "暂时无法生成智能回答，请联系管理员完成配置。"
        )
    return content