"""端到端冒烟测试：直接使用 Flask 测试客户端调用全部核心接口。

    python -m scripts.smoke_test
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

PASSED = []
FAILED = []


def _prepare_env():
    """使用独立的临时数据库/上传目录，避免污染开发数据。"""
    tmpdir = tempfile.mkdtemp(prefix="lab_smoke_")
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmpdir, "test.db").replace("\\", "/")
    os.environ["UPLOAD_FOLDER"] = os.path.join(tmpdir, "files")
    return tmpdir


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  [PASS] {name}")
    else:
        FAILED.append((name, detail))
        print(f"  [FAIL] {name} :: {detail}")


def call(client, method, path, token=None, json_body=None, data=None):
    headers = {}
    if token:
        headers["satoken"] = token
    if method == "GET":
        resp = client.get(path, headers=headers)
    else:
        if data is not None:
            resp = client.post(path, headers=headers, data=data)
        else:
            resp = client.post(path, headers=headers, json=json_body or {})
    try:
        payload = resp.get_json()
    except Exception:
        payload = None
    return resp, payload


def main():
    _prepare_env()
    from app import create_app
    from app.extensions import db

    app = create_app()
    with app.app_context():
        db.create_all()
        from scripts.seed import run_seed

        run_seed()

    client = app.test_client()

    print("== 认证 ==")
    _, r = call(client, "POST", "/api/login/loginIn",
                json_body={"account": "admin", "password": "admin123"})
    check("管理员登录", r and r.get("code") == "200", r)
    token = (r or {}).get("data", {}).get("token")

    _, r = call(client, "GET", "/api/login/info", token=token)
    check("登录态校验", r and r.get("code") == "200", r)

    _, r = call(client, "GET", "/api/login/info")
    check("未登录返回 399", r and r.get("code") == "399", r)

    _, r = call(client, "POST", "/api/login/loginIn",
                json_body={"account": "admin", "password": "wrong"})
    check("密码错误拦截", r and r.get("code") != "200", r)

    print("== 用户/小组 ==")
    _, r = call(client, "POST", "/api/group/queryGroupsList")
    check("小组列表", r and r.get("code") == "200" and isinstance(r["data"], list), r)

    _, r = call(client, "POST", "/api/group/queryGroupsByPage", token=token,
                json_body={"page": 1, "size": 10})
    check("小组分页", r and r.get("data", {}).get("grouplist") is not None, r)

    _, r = call(client, "POST", "/api/group/addGroup", token=token,
                json_body={"operator": "admin", "groupName": "冒烟测试组",
                           "leaderName": "演示用户", "reportFlag": 1})
    check("新增小组并任命组长", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/user/queryUserByPage", token=token,
                json_body={"operator": "admin", "page": 1, "size": 10})
    check("人员分页", r and r.get("data", {}).get("userList") is not None, r)

    _, r = call(client, "POST", "/api/user/queryUserMessage",
                json_body={"account": "demo"})
    check("用户详情", r and r.get("code") == "200" and r["data"]["account"] == "demo", r)

    _, r = call(client, "POST", "/api/user/queryRoleList")
    check("角色列表", r and len(r.get("data", [])) == 3, r)

    _, r = call(client, "POST", "/api/user/queryGroupUserAll", token=token)
    check("全部小组用户", r and r.get("code") == "200", r)

    print("== 签到 ==")
    _, r = call(client, "POST", "/api/record/queryStatusType", json_body={"account": "demo"})
    before = r["data"]["statusType"] if r and r.get("code") == "200" else None
    check("查询签到状态", before in (1, 2), r)

    _, r = call(client, "POST", "/api/record/checkIn", json_body={"account": "demo"})
    check("签到", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/record/checkIn", json_body={"account": "demo"})
    check("重复签到拦截", r and r.get("code") != "200", r)

    _, r = call(client, "POST", "/api/record/checkOut", json_body={"account": "demo"})
    check("签退", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/record/queryRecordByPage", json_body={"page": 1, "size": 10})
    check("签到记录分页", r and r.get("data", {}).get("list") is not None, r)

    _, r = call(client, "POST", "/api/record/querySignDurationWeek", json_body={"account": "demo"})
    check("本周签到曲线", r and len(r.get("data", [])) == 7, r)

    _, r = call(client, "POST", "/api/signDuration/querySignDurationByPage",
                json_body={"page": 1, "size": 10})
    check("签到时长分页", r and r.get("data", {}).get("list") is not None, r)

    _, r = call(client, "POST", "/api/signDuration/queryWeek", json_body={"list": ["demo"]})
    check("多人签到曲线", r and r.get("code") == "200", r)

    print("== 日报 ==")
    _, r = call(client, "POST", "/api/report/hasSubmittedToday", json_body={"account": "demo"})
    check("今日日报状态", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/report/reportSubmit",
                json_body={"workContent": "完成签到模块", "problems": "无", "plan": "编写测试", "account": "demo"})
    check("提交日报", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/report/queryReportByPage", json_body={"page": 1, "size": 10})
    check("日报分页", r and r.get("data", {}).get("reportList") is not None, r)

    _, r = call(client, "POST", "/api/user/timeline", json_body={"account": "demo"})
    check("历史回顾", r and r.get("code") == "200", r)

    print("== 请假 ==")
    now = datetime.now()
    _, r = call(client, "POST", "/api/leave/addLeave", token=token,
                json_body={"account": "demo",
                           "startDate": (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                           "endDate": (now + timedelta(days=1, hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                           "reason": "冒烟测试请假"})
    check("提交请假", r and r.get("code") == "200", r)
    leave_id = (r or {}).get("data", {}).get("id")

    _, r = call(client, "POST", "/api/leave/queryLeaveByPage", json_body={"page": 1, "size": 10, "state": "0"})
    check("请假分页", r and r.get("data", {}).get("leaveList") is not None, r)

    if leave_id:
        _, r = call(client, "POST", "/api/leave/approveLeave", token=token,
                    json_body={"id": leave_id, "handlers": "admin"})
        check("审批通过", r and r.get("code") == "200", r)

    print("== 会议 ==")
    start = (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    _, r = call(client, "POST", "/api/meeting/addMeeting", token=token,
                json_body={"meetingName": "冒烟测试会议", "description": "验证会议模块",
                           "startTime": start, "location": "13-404",
                           "memberList": ["演示用户"], "organizerAccount": "admin"})
    check("发布会议", r and r.get("code") == "200", r)
    meeting_id = (r or {}).get("data", {}).get("meetingId")

    _, r = call(client, "POST", "/api/meeting/queryMeetingByPage",
                json_body={"page": 1, "size": 10})
    check("会议分页", r and r.get("data", {}).get("MeetingsList") is not None, r)

    if meeting_id:
        _, r = call(client, "POST", "/api/meeting/queryMeetingByDate",
                    json_body={"account": "admin",
                               "queryDate": (now + timedelta(days=2)).strftime("%Y-%m-%d")})
        check("按日期查会议", r and r.get("code") == "200", r)

        _, r = call(client, "POST", "/api/meetingSignin/start", token=token,
                    json_body={"meetingId": meeting_id})
        check("开启会议签到", r and r.get("code") == "200", r)
        path = (r or {}).get("data", {}).get("signinPath", "")
        signin_token = path.split("token=")[-1] if "token=" in path else None

        if signin_token:
            _, r = call(client, "GET", f"/api/meetingSignin/selection?token={signin_token}")
            check("扫码读取会议信息", r and r.get("code") == "200"
                  and len(r["data"]["people"]) >= 1, r)

            _, r = call(client, "POST", "/api/meetingSignin/complete",
                        json_body={"token": signin_token, "groupName": "冒烟测试组", "account": "demo"})
            check("扫码签到", r and r.get("code") == "200", r)

        _, r = call(client, "POST", "/api/meetingSignin/board", json_body={"meetingId": meeting_id})
        check("签到大屏数据", r and r.get("code") == "200", r)

        _, r = call(client, "POST", "/api/meeting/queryMeetingAttendanceAudit",
                    json_body={"meetingId": meeting_id})
        check("出勤审核列表", r and r.get("code") == "200", r)

        _, r = call(client, "POST", "/api/meeting/getMeetingMinutes", token=token,
                    json_body={"meetingId": meeting_id})
        check("生成会议纪要", r and r.get("code") == "200", r)

        _, r = call(client, "POST", "/api/meetingSignin/end", token=token,
                    json_body={"meetingId": meeting_id})
        check("结束会议签到", r and r.get("code") == "200", r)

    print("== 系统配置/提醒 ==")
    _, r = call(client, "POST", "/api/systemConfig/queryReportType")
    check("查询发送配置", r and r.get("code") == "200" and "msg" in r, r)

    _, r = call(client, "POST", "/api/systemConfig/updateReportType", token=token,
                json_body={"configValue": "2"})
    check("更新发送配置", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/systemConfig/queryIsSkipHolidays")
    check("查询节假日配置", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/homeReminder/queryActive", token=token)
    check("首页提醒", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/homeReminder/acknowledge", token=token,
                json_body={"reminderType": "SIGN_DURATION"})
    check("确认提醒", r and r.get("code") == "200", r)

    print("== 其它 ==")
    _, r = call(client, "POST", "/api/course/queryCourseByUserList", json_body={"list": ["演示用户"]})
    check("课程查询", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/achievement/study/list", json_body={"page": 1, "size": 10})
    check("学习收获列表", r and r.get("code") == "200", r)

    _, r = call(client, "POST", "/api/fileRecord/queryFileRecordByPage", json_body={"page": 1, "size": 10})
    check("文件列表", r and r.get("data", {}).get("fileList") is not None, r)

    _, r = call(client, "POST", "/api/agent/ask", json_body={"prompt": "助手", "question": "你好"})
    check("智能问答", r and r.get("code") == "200", r)

    print("== 导出 ==")
    resp, _ = call(client, "POST", "/api/report/download", json_body={"page": 1, "size": 10})
    check("导出日报", resp is not None and resp.status_code == 200 and len(resp.data) > 0,
          resp.status_code if resp else None)

    resp, _ = call(client, "POST", "/api/signDuration/signDurationDownload",
                   json_body={"page": 1, "size": 10})
    check("导出签到时长", resp is not None and resp.status_code == 200, resp.status_code if resp else None)

    print()
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for name, detail in FAILED:
            print("  FAILED:", name, detail)
        sys.exit(1)


if __name__ == "__main__":
    main()