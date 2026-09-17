# 旧系统（Java）功能与接口梳理

> 目的：作为新 Flask 系统的功能基线。旧系统地址 `http://172.22.236.90/`，
> 前端为 Vue3 单页应用，后端为 Java（Sa-Token 鉴权）。
> 新系统在接口路径、请求体、响应结构上保持兼容，便于旧前端平滑切换。

## 1. 架构特征

| 项 | 旧系统 |
| --- | --- |
| 前端 | Vue3 + Element Plus + ECharts，axios `baseURL=/api` |
| 鉴权 | Sa-Token，请求头 `satoken: <token>`，同时带 `Authorization: Bearer <token>` |
| 响应格式 | `{"code":"200","data":...}` / `{"code":"500","message":"..."}`，部分接口用 `msg` |
| 未登录 code | `399`；无权限 `403` |
| 分页字段 | `page` / `size` / `dataCount` / `pageCount`，列表键各模块不同 |
| 文件导出 | `Content-Disposition: attachment; filename*=utf-8''...`，前端按 UTF-8 解析文件名 |

### 角色

| roleId | roleName | 说明 |
| --- | --- | --- |
| 1 | user | 普通用户 |
| 2 | groupLeader | 组长 |
| 3 | allLeader | 老师/总管人员（超管） |

## 2. 功能模块（前端路由）

```
/login                登录
/register             注册
/dashboard            首页（签到状态、今日会议、首页提醒）
/checkin              签到管理（签到/签退、签到显示、图表、统计、记录）
/report               报告管理（报告提交、报告记录）
/meeting              会议（会议发布、会议记录、会议签到）
/leave                请假管理（请假申请、请假记录、请假处理）
/achievement          成果管理（文件管理、获奖情况、学习收获）
/organization         组织管理（人员管理、小组管理、邮件配置）
/system               系统（发送配置、内容配置）
/analysis             个人分析（表单展示、图表分析、智能建议、历史回顾）
/portrait             画像分析（个人画像）
/profile              个人设置
/meeting/signin/checkin      扫码签到（公开）
/meeting/signin/:meetingId   会议签到大屏（allLeader）
```

## 3. 数据模型（由真实响应归纳）

### 3.1 用户 User
`account, userName, sex(0男/1女), phone, grade, email, groupName, stuNumber, className, inputDate, roleName, roleDescription, reportFlag`

- 注册字段：`account, password, confirmPassword, userName, sex, phone, grade, email, groupName, stuNumber(13位数字), className`
- 人员管理行：`account, userName, groupName, reportFlag, roleDescription`

### 3.2 小组 Group
`groupId, groupName, leaderAccount, leaderName, reportFlag, memberCount`

### 3.3 签到记录 SignRecord
`userName, groupName, startDate, endDate, reportDate`
规则：每人每天签到一次、签退一次；未签退记录以当天 `23:59:59` 结束。

### 3.4 签到时长 SignDuration
`userName, groupName, reportDate, signDuration(小时, 1 位小数)`

### 3.5 日报 Report
`userName, groupName, reportDate, workContent, problems, plan`（每人每天一条，可附件）

### 3.6 会议 Meeting / 成员 MeetingMember
会议：`meetingId, meetingName, reportDate, description, startTime(HH:mm:ss), location, organizerName, membersName, status, summary, keyword, files[], signinStatus, signinStartTime, signinEndTime`

签到状态：`0 未开启 / 1 进行中 / 2 已结束`

成员出勤：`userName, hasCheckedIn, checkInTime, status(2=请假), leaveReason`

### 3.7 请假 LeaveRecord
`id, reportDate, startDate, endDate, userName, reason, remarks, allowedFlag`
`allowedFlag：0 待审核 / 1 已通过 / 2 已拒绝`

### 3.8 文件 FileRecord
`id, fileName, filePath, fileSize, uploadedBy, userName, uploadedAt, fileType, sourceType, relatedId`
`sourceType：1 日报周报 / 2 会议共享 / 3 项目文件`

### 3.9 系统配置 SystemConfig
- `report_type`：`0 不发送邮件 / 1 日报 / 2 周报`（响应走 `msg` 字段）
- `skip_holidays`：`0 不跳过 / 1 跳过节假日`

### 3.10 首页提醒 HomeReminder
`reminderType, title, message, cycleKey`
- `REPORT`：超过 60 小时未提交日报
- `SIGN_DURATION`：本周签到时长不足 24 小时

### 3.11 邮件分组 EmailGroup
`account, userName, email, groupList:[{groupId, groupName, memberAccount, excludeFlag}]`

### 3.12 课程 Course
按用户 + 星期（1-5）存储 12 节课：`courseFirst ... courseTwelfth`

### 3.13 成果 Achievement
`name, date, content`（学习收获 / 获奖情况）

## 4. 接口清单（旧 → 新 已实现）

| 方法 | 路径 | 说明 | 新系统 |
| --- | --- | --- | --- |
| POST | `/api/login/loginIn` | 登录 | ✅ |
| POST | `/api/login/register` | 注册 | ✅ |
| GET | `/api/login/info` | 登录态校验 | ✅ |
| POST | `/api/user/queryUserMessage` | 用户详情 | ✅ |
| POST | `/api/user/queryUserByPage` | 人员分页 | ✅ |
| POST | `/api/user/queryGroupUserAll` | 全部小组及成员 | ✅ |
| POST | `/api/user/queryRoleList` | 角色列表 | ✅ |
| POST | `/api/user/updateUser` | 修改成员小组/日报开关 | ✅ |
| POST | `/api/user/deleteUser` | 删除成员 | ✅ |
| POST | `/api/user/appointGroupLeader` | 任命组长 | ✅ |
| POST | `/api/user/updateUserRole` | 调整角色 | ✅ |
| POST | `/api/user/timeline` | 历史回顾 | ✅ |
| POST | `/api/user/generatePersonalSummary` | 个人总结（AI） | ✅ |
| POST | `/api/user/download` | 人员统计导出 | ✅ |
| POST | `/api/group/queryGroupsList` | 小组名列表 | ✅ |
| POST | `/api/group/queryGroupsByPage` | 小组分页 | ✅ |
| POST | `/api/group/queryManageableGroups` | 可管理小组 | ✅ |
| POST | `/api/group/addGroup` | 新增小组 | ✅ |
| POST | `/api/group/updateGroup` | 修改小组 | ✅ |
| POST | `/api/group/deleteGroup` | 删除小组 | ✅ |
| POST | `/api/group/download` | 小组导出 | ✅ |
| POST | `/api/record/checkIn` | 签到 | ✅ |
| POST | `/api/record/checkOut` | 签退 | ✅ |
| POST | `/api/record/queryStatusType` | 签到状态 | ✅ |
| POST | `/api/record/queryRecordByPage` | 签到记录 | ✅ |
| POST | `/api/record/querySignDurationWeek` | 本周签到曲线 | ✅ |
| POST | `/api/record/queryGroupSignDuration` | 各组时长分布 | ✅ |
| POST | `/api/record/checkInRecordDownload` | 签到记录导出 | ✅ |
| POST | `/api/signDuration/querySignDurationByPage` | 时长分页 | ✅ |
| POST | `/api/signDuration/queryWeek` | 多人曲线 | ✅ |
| POST | `/api/signDuration/signDurationDownload` | 时长导出 | ✅ |
| POST | `/api/report/reportSubmit` | 提交日报（multipart） | ✅ |
| POST | `/api/report/hasSubmittedToday` | 今日是否提交 | ✅ |
| POST | `/api/report/queryReportByPage` | 日报分页 | ✅ |
| POST | `/api/report/download` | 日报明细导出 | ✅ |
| POST | `/api/report/downloadSummary` | 周/月汇总导出 | ✅ |
| POST | `/api/meeting/addMeeting` | 发布会议 | ✅ |
| POST | `/api/meeting/queryMeetingByPage` | 会议分页 | ✅ |
| POST | `/api/meeting/queryMeetingByDate` | 按日期查会议 | ✅ |
| POST | `/api/meeting/updateSummary` | 保存纪要 | ✅ |
| POST | `/api/meeting/updateKeyword` | 保存关键字 | ✅ |
| POST | `/api/meeting/getMeetingMinutes` | 生成纪要（AI） | ✅ |
| POST | `/api/meeting/queryMeetingAttendanceAudit` | 出勤审核 | ✅ |
| POST | `/api/meeting/uploadReport` | 上传会议材料 | ✅ |
| POST | `/api/meeting/download` | 会议导出 | ✅ |
| POST | `/api/userMeeting/leaveMeeting` | 会议请假 | ✅ |
| POST | `/api/meetingSignin/board` | 签到大屏 | ✅ |
| POST | `/api/meetingSignin/start` | 开启签到 | ✅ |
| POST | `/api/meetingSignin/end` | 结束签到 | ✅ |
| POST | `/api/meetingSignin/status` | 修改成员状态 | ✅ |
| POST | `/api/meetingSignin/complete` | 扫码签到 | ✅ |
| GET | `/api/meetingSignin/selection?token=` | 扫码读取信息 | ✅ |
| POST | `/api/leave/addLeave` | 提交请假 | ✅ |
| POST | `/api/leave/queryLeaveByPage` | 请假分页 | ✅ |
| POST | `/api/leave/approveLeave` | 通过 | ✅ |
| POST | `/api/leave/notApprovedLeave` | 拒绝 | ✅ |
| POST | `/api/fileRecord/queryFileRecordByPage` | 文件分页 | ✅ |
| POST | `/api/fileRecord/downloadFile` | 文件下载 | ✅ |
| POST | `/api/systemConfig/queryReportType` | 查询发送配置 | ✅ |
| POST | `/api/systemConfig/updateReportType` | 更新发送配置 | ✅ |
| POST | `/api/systemConfig/queryIsSkipHolidays` | 查询节假日配置 | ✅ |
| POST | `/api/systemConfig/updateIsSkipHolidays` | 更新节假日配置 | ✅ |
| POST | `/api/homeReminder/queryActive` | 首页提醒 | ✅ |
| POST | `/api/homeReminder/acknowledge` | 确认提醒 | ✅ |
| POST | `/api/emailGroup/queryEmailGroup` | 邮件分组查询 | ✅ |
| POST | `/api/emailGroup/addEmailGroupByUser` | 新增订阅 | ✅ |
| POST | `/api/emailGroup/updateEmailGroupByUser` | 修改订阅 | ✅ |
| POST | `/api/emailGroup/deleteEmailGroupByUser` | 删除订阅 | ✅ |
| POST | `/api/course/queryCourseByUserList` | 课程查询 | ✅ |
| POST | `/api/achievement/study/list` | 学习收获 | ✅ |
| POST | `/api/agent/ask` | 智能问答 | ✅ |

## 5. 新旧差异与后续待办

1. **鉴权**：旧系统 Sa-Token（服务端 Session），新系统 JWT（无状态）。前端无需改动，
   仍以 `satoken` 头携带 token。
2. **会议纪要 / 个人总结 / 智能问答**：旧系统调用外部大模型；新系统在
   `AI_API_BASE/AI_API_KEY/AI_MODEL` 未配置时使用本地规则文本兜底。
3. **节假日判断**：当前按周末近似，后续可接入节假日表 / 第三方日历。
4. **邮件发送（日报/周报）**：配置已落库，发送任务尚未实现，建议后续接入
   APScheduler/Celery + SMTP。
5. **数据迁移**：旧库为 MySQL。可直接用 SQLAlchemy 连接旧库做一次性迁移脚本
   （字段已按旧结构命名，映射成本低）。
6. **图片/头像、获奖情况完整 CRUD**：已建模型，接口可继续补齐。