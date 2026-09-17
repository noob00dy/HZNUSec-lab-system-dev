# 实验室智能管理系统（Flask 重构版）

基于 Flask + SQLAlchemy 重写原 Java 版实验室管理系统。
新后端在**接口路径、请求体、响应结构**上与原系统保持兼容，原 Vue 前端可平滑切换。

## 功能模块

- **认证**：登录 / 注册 / 登录态校验（JWT，兼容 `satoken` 请求头）
- **签到**：签到、签退、状态查询、签到记录、签到时长统计与多维度图表、Excel 导出
- **日报**：提交（支持附件）、今日状态、记录查询、明细/周汇总导出
- **会议**：发布、分页查询、会议材料上传、纪要生成、出勤审核、会议请假
- **会议签到**：开启/结束签到、扫码签到页、签到大屏轮询、手动改状态
- **请假**：申请、记录查询、通过/拒绝审批
- **组织管理**：人员管理、小组管理（增删改、任命组长）、邮件分组订阅
- **系统配置**：日报/周报发送方式、是否跳过节假日
- **成果**：文件管理、学习收获、获奖情况
- **分析/画像**：历史回顾、个人总结、智能问答（可选接入大模型）

> 旧系统完整功能与接口梳理见 [`docs/legacy-system.md`](docs/legacy-system.md)。

## 技术栈

| 组件 | 选型 |
| --- | --- |
| Web 框架 | Flask 3 |
| ORM | Flask-SQLAlchemy / SQLAlchemy 2 |
| 数据库 | 开发默认 SQLite，生产 MySQL（PyMySQL） |
| 鉴权 | PyJWT（Bearer / satoken 双兼容） |
| 导出 | openpyxl |
| 跨域 | Flask-Cors |
| 二维码 | qrcode + Pillow |

## 快速开始

```bash
# 1. 创建虚拟环境（可选）
python -m venv .venv && .venv\Scripts\activate   # Windows
# source .venv/bin/activate                       # Linux/macOS

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env      # Windows
# cp .env.example .env      # Linux/macOS

# 4. 初始化数据（角色、管理员 admin/admin123、演示用户 demo/demo123）
flask --app run.py seed

# 5. 启动
python run.py
# 访问 http://127.0.0.1:5000/api/health
```

### 使用 MySQL

```env
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/lab_system?charset=utf8mb4
```

创建数据库后执行 `flask --app run.py init-db && flask --app run.py seed`。

## 冒烟测试

```bash
python -m scripts.smoke_test
```

覆盖认证、用户/小组、签到、日报、请假、会议与扫码签到、系统配置、导出等，
共 47 项断言，全部通过后退出码为 0。

## 目录结构

```
app/
├── __init__.py            应用工厂、错误处理、CLI
├── config.py              配置（环境变量）
├── extensions.py          SQLAlchemy 实例
├── models/                数据模型
│   ├── user.py            Role / Group / User
│   ├── attendance.py      SignRecord / SignDuration
│   ├── report.py          Report
│   ├── meeting.py         Meeting / MeetingMember
│   ├── leave.py           LeaveRecord
│   ├── file.py            FileRecord
│   ├── system.py          SystemConfig / HomeReminder
│   ├── email.py           EmailGroup
│   ├── course.py          Course
│   └── achievement.py     Achievement
├── api/                   蓝图（按旧系统路径划分）
│   ├── auth.py            /api/login/*
│   ├── user.py            /api/user/*
│   ├── group.py           /api/group/*
│   ├── record.py          /api/record/*
│   ├── sign_duration.py   /api/signDuration/*
│   ├── report.py          /api/report/*
│   ├── meeting.py         /api/meeting/*、/api/userMeeting/*
│   ├── meeting_signin.py  /api/meetingSignin/*
│   ├── leave.py           /api/leave/*
│   ├── file_record.py     /api/fileRecord/*
│   ├── system_config.py   /api/systemConfig/*
│   ├── home_reminder.py   /api/homeReminder/*
│   ├── email_group.py     /api/emailGroup/*
│   ├── course.py          /api/course/*
│   ├── achievement.py     /api/achievement/*
│   ── agent.py           /api/agent/*
├── services/              业务逻辑
│   ├── sign_service.py    签到时长计算、聚合统计
│   ├── report_service.py  日报提交、汇总
│   ├── reminder_service.py 首页提醒
│   └── summary_service.py 纪要/总结/智能问答
└── utils/                 响应、鉴权、分页、Excel、文件、时间
scripts/
├── seed.py                初始化数据
└── smoke_test.py          端到端冒烟测试
docs/legacy-system.md      旧系统功能与接口梳理
```

## 接口约定

- 统一响应：成功 `{"code":"200","data":...}`，失败 `{"code":"4xx/5xx","message":"..."}`；
  系统配置类接口返回 `{"code":"200","msg":"..."}`。
- 鉴权：请求头 `satoken: <token>` 或 `Authorization: Bearer <token>`。
- 未登录返回 `code=399`；无权限返回 `code=403`。
- 分页：请求 `page`/`size`，响应含 `dataCount`/`pageCount`，列表键与旧系统一致
  （如 `userList`、`reportList`、`MeetingsList`、`leaveList`、`fileList`）。

## 后续规划

1. 日报/周报邮件定时发送（APScheduler/Celery + SMTP）
2. 从旧 Java 库一次性迁移数据（脚本）
3. 节假日表 / 校历接入，替换周末近似判断
4. 获奖情况、项目文件完整 CRUD 与权限细分
5. 会议签到 WebSocket 推送，替代轮询
6. Alembic 数据库迁移与生产部署（Gunicorn + Nginx）