# 数学建模校赛网站 — API 文档（初版）

> 说明：REST 风格，JSON 作为主要数据交换格式；文件上传采用 `multipart/form-data`；所有需要授权的接口使用 Bearer Token（JWT）。时间均为 ISO8601，使用 UTC+8。

## 通用约定
- 认证：`Authorization: Bearer <token>`
- 成功响应：`{ code: 0, message: 'ok', data: ..., requestId?: '...' }`
- 失败响应：`{ code: <非0>, message: '<错误描述>', details?: any, requestId?: '...' }`
- 分页参数：`page`（默认 1），`pageSize`（默认 20，上限 100）
- 角色：`student`、`teacher`、`admin`
- 错误码（示例）：
  - 0 成功
  - 1001 参数错误
  - 1002 未认证/令牌无效
  - 1003 权限不足
  - 1004 资源不存在
  - 1005 状态不允许（如未报名、未开赛、已截止）
  - 1006 并发冲突
  - 1007 文件类型/大小不合法
  - 1008 频率限制/验证码校验失败
  - 1999 服务器内部错误

### HTTP 状态码映射（统一约定）
- 200 OK / 201 Created / 204 No Content：成功。
- 400 Bad Request：参数错误/字段校验失败（示例：`code=1001`）。
- 401 Unauthorized：未认证或令牌无效/过期（示例：`code=1002`）。
- 403 Forbidden：已认证但权限不足（示例：`code=1003`）。
- 404 Not Found：资源不存在（示例：`code=1004`）。
- 409 Conflict：并发/业务冲突（示例：队伍重复加入，`code=1006`）。
- 429 Too Many Requests：频率限制或验证码校验失败（示例：`code=1008`）。
- 500 Internal Server Error / 503 Service Unavailable：服务器异常/依赖不可用（示例：`code=1999`）。

### 字段级错误结构（建议）
当出现 400 类错误时，`details` 中返回字段错误列表：
```json
{
  "code": 1001,
  "message": "参数校验失败",
  "details": {
    "fieldErrors": [
      { "field": "email", "message": "邮箱格式不正确" },
      { "field": "password", "message": "至少8位且包含字母与数字" }
    ]
  },
  "requestId": "r-77b1..."
}
```

### 诊断信息与追踪
- 所有响应可包含 `requestId` 或 `traceId`，用于日志与问题定位。
- 后端在日志中记录该标识，以便跨服务检索。

## 模块一：认证与账号
### 学生注册
- POST `/api/auth/student/register`
- Body：
```json
{
  "studentId": "2023123456", // 学号（唯一）
  "name": "张三",
  "college": "数学学院",
  "class": "数模2201",
  "email": "zs@example.com", // 必填，用于邮箱验证码与找回
  "password": "******"
}
```
- 响应：`{ code: 0 }`

### 登录（分角色接口）
- 管理员专用：POST `/api/auth/adminManager-login`
  - Body：`{ account: string, password: string }`
  - 响应：同下方统一响应格式，`role=admin`
- 学生专用：POST `/api/auth/student-login`
  - Body：`{ studentId?: string, email?: string, password: string }`（`studentId` 与 `email` 至少提供一个）
  - 响应：同下方统一响应格式，`role=student`
- 教师专用：POST `/api/auth/teacher-login`
  - Body：`{ account: string, password: string }`
  - 响应：同下方统一响应格式，`role=teacher`

#### 统一成功响应格式
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "token": "<jwt>",
    "role": "student|teacher|admin",
    "profile": { /* 基本信息 */ }
  }
}
```

#### 兼容通用登录（待迁移）
- POST `/api/auth/login`（当前默认管理员登录；建议前端逐步迁移到分角色接口）

### 教师账号管理（管理员）
- POST `/api/admin/teachers/generate`
  - 认证：`Authorization: Bearer <admin_jwt>`（仅管理员角色）
  - Body：
    ```json
    { "names": ["张三", "李四", "王五"] }
    ```
  - 规则：
    - 为每个姓名生成一个教师账号，账号格式为 `tNNN`（例如 `t001`、`t002`），按现有账号最大序号递增。
    - 默认初始密码：`Math123@123`。
    - 若数据库已存在同名教师，返回状态 `exists`，不重复创建（`tempPassword` 为空）。
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "ok",
      "data": {
        "rows": [
          { "name": "张三", "account": "t002", "tempPassword": "Math123@123", "status": "ok" },
          { "name": "李四", "account": "t003", "tempPassword": "Math123@123", "status": "ok" },
          { "name": "王五", "account": "t001", "tempPassword": null, "status": "exists" }
        ],
        "created": 2
      }
    }
    ```
  - 失败响应：
    - `400` 参数错误（如 `names` 为空）示例：
      ```json
      { "code": 1001, "message": "参数校验失败：names 为空" }
      ```
    - `401` 未认证/令牌无效或过期：`{ "code": 1002, "message": "令牌无效/已过期" }`
    - `403` 权限不足（非管理员）：`{ "code": 1003, "message": "权限不足：需要管理员角色" }`

- POST `/api/admin/teachers/password/init`
  - 认证：`Authorization: Bearer <admin_jwt>`（仅管理员角色）
  - Body：
    ```json
    { "accounts": ["t001", "t002"], "all": false }
    ```
    - 支持两种方式：
      - 指定账号列表：传入 `accounts`（数组），`all=false` 或省略。
      - 一键初始化全部教师：`{ "all": true }`。若同时提供 `accounts`，优先按 `all` 处理。
  - 规则：
    - 将目标教师密码重置为默认初始密码：`Math123@123`。
    - 返回每个教师的处理状态：`ok`（已重置）、`not_found`（账号不存在）。
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "ok",
      "data": {
        "rows": [
          { "account": "t001", "name": "王五", "status": "ok" },
          { "account": "t999", "name": null, "status": "not_found" }
        ],
        "updated": 1,
        "defaultPassword": "Math123@123"
      }
    }
    ```
  - 失败响应：
    - `400` 参数错误（如 `accounts` 非数组且 `all` 非真）：
      ```json
      { "code": 1001, "message": "参数校验失败：accounts 必须为数组或设置 all=true" }
      ```
    - `401` 未认证/令牌无效或过期：`{ "code": 1002, "message": "令牌无效/已过期" }`
    - `403` 权限不足（非管理员）：`{ "code": 1003, "message": "权限不足：需要管理员角色" }`

- GET `/api/admin/teachers/password/export`
  - 认证：`Authorization: Bearer <admin_jwt>`（仅管理员角色）
  - 描述：导出 CSV 文件（`teachers-passwords.csv`），包含列：`account,name,password`。
  - 规则：
    - 若教师当前密码仍为默认密码（`Math123@123`），则在 `password` 列显示默认密码；否则留空，避免泄露真实密码。
    - 返回受控下载响应，头部包含 `Content-Disposition: attachment; filename=teachers-passwords.csv`。
  - 失败响应：
    - `401` 未认证/令牌无效或过期：`{ "code": 1002, "message": "令牌无效/已过期" }`
    - `403` 权限不足（非管理员）：`{ "code": 1003, "message": "权限不足：需要管理员角色" }`

### 忘记密码请求（邮箱验证码）
- POST `/api/auth/forgot`
- Body：`{ account: string }`（学生使用学号或邮箱，教师/管理员使用账号或绑定邮箱）
- 响应：`{ code: 0 }`

### 重置密码（使用邮箱验证码或重置令牌）
- POST `/api/auth/reset`
- Body：`{ token: string, newPassword: string }`（`token` 为邮箱验证码或基于验证码颁发的短期重置令牌）
- 响应：`{ code: 0 }`

### 修改密码（已登录）
- POST `/api/auth/change`
- Body：`{ oldPassword: string, newPassword: string }`
- 响应：`{ code: 0 }`

## 模块二：赛季（赛事活动）
### 创建赛季（管理员）
- POST `/api/seasons`
- Body：
```json
{
  "name": "2025校赛",
  "signupStart": "2025-03-01T00:00:00+08:00",
  "signupEnd": "2025-03-10T23:59:59+08:00",
  "startTime": "2025-03-15T09:00:00+08:00",
  "submitDeadline": "2025-03-18T21:00:00+08:00",
  "reviewStart": "2025-03-19T09:00:00+08:00",
  "reviewEnd": "2025-03-25T18:00:00+08:00"
}
```
- 响应：`{ code: 0, data: { id: "..." } }`

### 获取赛季列表（公开/已登录）
- GET `/api/seasons`
- Query：`status?=signup|running|review|ended`
- 响应：`{ code: 0, data: [ { id, name, status, timeRanges... } ] }`

### 获取赛季详情
- GET `/api/seasons/{seasonId}`
- 响应：赛季配置与状态

## 模块三：报名与队伍（学生）
### 报名改为“通过队伍报名”
说明：已弃用旧接口 `POST /api/seasons/{seasonId}/signup`。学生需创建或加入队伍后，系统自动完成报名（按学生维度记录）。

### 创建队伍并自动报名（需登录）
- POST `/api/student/competitions/{season_id}/teams`
- Body：`{ name: string }`
- 行为：
  - 校验报名是否开放（处于报名窗口或 `allow_signup=true`）。
  - 若学生在该赛季已有队伍，直接返回队伍信息（幂等）。
  - 创建队伍成为队长，自动生成一个 7 天有效的加入令牌，并自动为学生记录报名。
- 成功响应示例：
```json
{ "code": 0, "message": "ok", "data": { "id": 1, "season_id": 123, "name": "数模战队", "captain_id": 2, "status": "approved", "locked": false, "members": [ { "id": 2, "student_id": "20230001", "name": "学生一号", "role": "captain" } ], "join_token": { "token": "abcd...", "expires_at": "2025-03-08T12:00:00+08:00" } } }
```

### 使用令牌加入队伍并自动报名（需登录）
- POST `/api/student/teams/join`
- Body：`{ token: string }`
- 行为：
  - 校验令牌有效期与报名是否开放。
  - 若学生在该赛季已有队伍，直接返回该队伍信息（幂等）。
  - 成功加入队伍后，自动为学生记录报名，加入请求记入审计历史。
- 成功响应示例：同“创建队伍并自动报名”。

### 查询我在指定赛季的队伍（需登录）
- GET `/api/student/competitions/{season_id}/my-team`
- 响应：`{ code: 0, data: null | TeamDetail }`

### 队长生成新的加入令牌（需登录，且为队长）
- POST `/api/student/teams/{team_id}/join-token`
- 行为：失效旧令牌，生成新的 7 天有效令牌。
- 响应：`{ code: 0, data: { token, expires_at } }`

### 创建队伍
- POST `/api/teams`
- Body：`{ seasonId: string, name: string }`
- 约束：报名期内；若已在队伍中则不允许创建；最多人数 3。
- 响应：`{ code: 0, data: { teamId: "...", joinToken: "..." } }`

### 生成/旋转加入 Token（队长）
- POST `/api/teams/{teamId}/token/rotate`
- 响应：`{ code: 0, data: { joinToken: "...", expiresAt: "..." } }`

### 加入队伍（使用 Token）
- POST `/api/teams/join`
- Body：`{ teamId: string, token: string }`
- 响应：`{ code: 0 }`

### 查看我的队伍
- GET `/api/teams/me?seasonId=...`
- 响应：队伍详情、成员列表、是否满员、锁定状态

### 退出队伍（报名期内）
- POST `/api/teams/{teamId}/leave`
- 响应：`{ code: 0 }`

### 管理员审核队伍
- GET `/api/admin/teams?seasonId=...&status=pending|approved|locked`
- POST `/api/admin/teams/{teamId}/delete`
- POST `/api/admin/teams/{teamId}/lock` / `/unlock`
- POST `/api/admin/teams/{teamId}/transfer-captain` Body：`{ newCaptainId: string }`

## 模块四：赛题文件（管理员上传、学生下载）
### 上传赛题（管理员）
- POST `/api/seasons/{seasonId}/problems`
- FormData：`files[]`（pdf/zip），`visibleAfterStart=true`
- 响应：`{ code: 0, data: [{ id, filename, size, hash }] }`

### 管理员：竞赛管理
说明：新增了管理员创建竞赛与上传赛题ZIP（覆盖保存）的接口。

- POST `/api/admin/competitions`
  - 认证：需要管理员 `Authorization: Bearer <token>`
  - Body（JSON）：
    - `name`: string，竞赛名称，唯一且非空
    - `start_time`: string(ISO8601)，竞赛开始时间
    - `end_time`: string(ISO8601)，竞赛结束时间，必须晚于 `start_time`
    - `signup_start?`: string(ISO8601，可选)
    - `signup_end?`: string(ISO8601，可选)
    - `review_start?`: string(ISO8601，可选)
    - `review_end?`: string(ISO8601，可选)
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "ok",
      "data": {
        "season": {
          "id": 123,
          "name": "2025校赛",
          "start_time": "2025-10-05T09:00:00Z",
          "end_time": "2025-10-06T09:00:00Z",
          "status": "未开始"
        }
      }
    }
    ```
  - 失败响应：
    - 400 参数校验失败（如结束时间早于开始时间、name为空）：
      ```json
      { "code": 1001, "message": "参数校验失败：结束时间必须晚于开始时间" }
      ```
    - 409 竞赛名称已存在：
      ```json
      { "code": 1004, "message": "竞赛名称已存在" }
      ```
    - 401 未认证或令牌无效：标准 FastAPI 错误响应

- POST `/api/admin/competitions/{seasonId}/excellent/upload`
  - 认证：需要管理员 `Authorization: Bearer <token>`
  - FormData：
    - `file`: 优秀作品文件（仅支持 `.zip` 或 `.pdf`）
    - `summary?`: 作品摘要（可选，字符串）
    - `score?`: 评分（可选，数字）
    - `allow_download?`: 是否允许下载（可选，布尔）
    - `team_id?`: 关联队伍ID（可选，数字）
    - `submission_id?`: 关联提交ID（可选，数字）
  - 行为：
    - 校验赛季存在；校验文件类型（仅 zip/pdf）。
    - 查找或创建 `ExcellentWork`（若提供 `team_id` 或 `submission_id` 则尝试复用同一季下的记录），更新摘要/评分/下载许可等元信息。
    - 将文件保存到 `uploads/excellent/season_<seasonId>/work_<workId>/<filename>`，计算 `sha256` 与 `size`，在 `ExcellentWorkFile` 表中追加记录（保留多文件）。
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "ok",
      "data": {
        "work_id": 456,
        "season_id": 123,
        "filename": "excellent.zip",
        "size": 204800,
        "hash": "<sha256>",
        "path": "uploads/excellent/season_123/work_456/excellent.zip",
        "uploaded_at": "2025-10-05T09:00:00Z",
        "summary": "模型简洁，结果稳定",
        "score": 92.5,
        "allow_download": true
      }
    }
    ```
  - 失败响应：
    - 404 竞赛不存在：
      ```json
      { "code": 1005, "message": "指定的竞赛不存在" }
      ```
    - 400 文件类型错误（非 zip/pdf）：
      ```json
      { "code": 1001, "message": "文件类型错误：仅支持 .zip 或 .pdf" }
      ```
    - 401 未认证或令牌无效：标准 FastAPI 错误响应

- POST `/api/admin/competitions/{seasonId}/problems/upload`
  - 认证：需要管理员 `Authorization: Bearer <token>`
  - FormData：
    - `file`: ZIP 文件（仅支持 `.zip`）
  - 行为：将 ZIP 覆盖保存到后端目录 `uploads/problems/season_<seasonId>.zip`，并在数据库 `ProblemFile` 表中创建/更新记录（包含 `filename`、`size`、`hash`、`path`、`uploaded_at` 等）
  - 成功响应：
    ```json
    {
      "code": 0,
      "message": "ok",
      "data": {
        "season_id": 123,
        "filename": "problems.zip",
        "size": 1024,
        "hash": "<sha256>",
        "path": "uploads/problems/season_123.zip",
        "uploaded_at": "2025-10-05T09:00:00Z"
      }
    }
    ```
  - 失败响应：
    - 404 竞赛不存在：
      ```json
      { "code": 1005, "message": "指定的竞赛不存在" }
      ```
    - 400 文件类型错误（非zip）：
      ```json
      { "code": 1001, "message": "文件类型错误：仅支持 .zip" }
      ```
    - 401 未认证或令牌无效：标准 FastAPI 错误响应

### 列出赛题（学生在开赛后可见）
- GET `/api/seasons/{seasonId}/problems`
- 响应：赛题文件列表（带下载地址或需二次获取）

### 获取赛题下载地址（授权）
- GET `/api/problems/{problemId}/download`
- 响应：`{ code: 0, data: { url: "<signedUrl>" } }`

## 模块五：作品提交（学生）
### 上传作品
- POST `/api/teams/{teamId}/submissions`
- 约束：提交截止前；仅队伍成员；大小与类型校验。
- FormData：`file`（zip/pdf/其他），`note`（可选）
- 响应：`{ code: 0, data: { submissionId, version, uploadedAt } }`

### 获取队伍提交记录
- GET `/api/teams/{teamId}/submissions`
- 响应：`{ code: 0, data: [ { id, version, note, uploadedAt, hash } ] }`

### 获取最终版信息
- GET `/api/teams/{teamId}/final-submission`
- 响应：最终版提交信息（评审使用）

## 模块六：评审打分（教师）
### 列出待评作品
- GET `/api/reviews/pending?seasonId=...&onlyUnscored=true`
- 响应：队伍与提交信息（隐去成员信息，若启用匿名）

### 获取评分维度配置（管理员设置）
- GET `/api/review-config?seasonId=...`
- 响应：`{ dimensions: [ { key, name, weight, maxScore } ], requireTeacherCount: 3 }`

### 提交评分
- POST `/api/reviews/{submissionId}`
- Body：
```json
{
  "scores": [
    { "key": "modeling", "score": 85 },
    { "key": "algorithm", "score": 80 },
    { "key": "writing", "score": 75 },
    { "key": "innovation", "score": 88 }
  ],
  "comment": "总体表现良好，建议改进算法效率。"
}
```
- 响应：`{ code: 0 }`

### 修改评分（评审期内）
- POST `/api/reviews/{submissionId}/update`
- Body 同上；响应 `{ code: 0 }`

### 查看评分进度与我的评分
- GET `/api/reviews/mine?seasonId=...`
- 响应：教师已评分列表与状态

### 汇总成绩（管理员）
- GET `/api/admin/scoreboard?seasonId=...`
- 响应：队伍总分、排名、维度分、人均分、去极值策略说明

## 模块七：教师账号管理（管理员）
### 批量导入教师
- POST `/api/admin/teachers/import`
- FormData：`file`（CSV），字段示例：`account,name,email(optional)`
- 响应：`{ code: 0, data: { imported: 100, duplicates: 2, defaultPasswordPolicy: "digits-only" } }`

### 重置教师初始密码
- POST `/api/admin/teachers/{teacherId}/reset-password`
- 响应：`{ code: 0, data: { tempPassword: "123456" } }`（首次登录强制改密）

## 模块八：历年优秀作品
### 列表与详情（公开/已登录）
- GET `/api/excellent-works?seasonId?=...`
- GET `/api/excellent-works/{workId}`
- 响应：摘要、分数、下载策略（若允许则提供签名地址）

## 模块九：系统与日志
### 操作日志（管理员）
- GET `/api/admin/audit/logs?actor_type=...&actor_id=...&action=...&object_type=...&object_id=...&start_time=...&end_time=...&page=1&page_size=20`（已实现）
- 响应：操作时间、操作者、对象、动作、详情
- 导出 CSV（已实现）：
  - GET `/api/admin/audit/logs/export?actor_type=...&actor_id=...&action=...&object_type=...&object_id=...&start_time=...&end_time=...`
  - 响应：`Content-Disposition: attachment; filename=audit-logs.csv`

#### 定期导出（脚本）
- 提供独立脚本：`backend/scripts/export_audit_logs.py`
- 用法示例：
  - 导出昨日全部：
    `python3 backend/scripts/export_audit_logs.py --start 2025-10-04 --end 2025-10-05`
  - 仅管理员的成绩导出动作：
    `python3 backend/scripts/export_audit_logs.py --actor-type admin --action scores.export --output exports/audit-logs-admin-scores.csv`
  - 关闭 BOM：
    `python3 backend/scripts/export_audit_logs.py --no-bom`
  - 定时任务（macOS cron 示例）：
    `0 2 * * * cd /path/to/repo && /usr/bin/env python3 backend/scripts/export_audit_logs.py --start "$(date -v-1d +%Y-%m-%d)" --end "$(date +%Y-%m-%d)" --output "exports/audit-logs-$(date -v-1d +%Y%m%d).csv"`

### 登录日志（管理员）
- GET `/api/admin/login-logs?role=student|teacher|admin&success=true|false`

## 模块十：通用文件与下载策略
- 所有下载类接口返回签名 URL 或走受控下载通道，避免直链暴露。
- 上传进行哈希校验与病毒扫描（可选）。

## 附：数据模型概览（简版）
- Student：id, studentId, name, college, class, email, passwordHash
- Teacher：id, account, name, email?, passwordHash, active
- Admin：id, account, name, passwordHash
- Season：id, name, signupStart, signupEnd, startTime, submitDeadline, reviewStart, reviewEnd, status
- Team：id, seasonId, name, captainId, memberIds[], joinToken, tokenExpiresAt, locked
- ProblemFile：id, seasonId, filename, size, hash, visibleAfterStart
- Submission：id, teamId, seasonId, fileInfo{filename,size,hash}, version, note, uploadedAt
- ReviewConfig：seasonId, dimensions[{key,name,weight,maxScore}], requireTeacherCount
- Review：id, submissionId, teacherId, scores[{key,score}], comment, updatedAt
- ExcellentWork：id, seasonId, teamId, submissionId, summary, score, allow_download
- ExcellentWorkFile：id, workId, filename, size, hash, path, uploadedAt

（本 API 文档为初版，待需求确认后可进一步细化鉴权、状态机与错误码表。）
### 发送邮箱验证码（通用）
- POST `/api/auth/send-email-code`
- Body：`{ email: string, purpose: "register|login2fa|forgot|sensitive" }`
- 响应：`{ code: 0 }`

### 校验邮箱验证码（通用）
- POST `/api/auth/verify-email-code`
- Body：`{ email: string, purpose: string, code: string }`
- 响应：`{ code: 0, data: { verified: true } }`

## 模块零：公开接口与学生报名（与实现对齐）

说明：以下接口已在后端实现，并已在前端首页调用展示与交互，现将正式文档对齐，替换初版中“报名赛季：POST /api/seasons/{seasonId}/signup”的旧路径描述。

### 列出开放报名的竞赛（公开）
- GET `/api/public/open-competitions`
- 说明：筛选满足报名开放条件的赛季（`signup_start <= now <= signup_end` 或 `allow_signup = true`），按报名开始时间升序返回。
- 响应示例：
```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": 123,
      "name": "2025校赛",
      "signup_start": "2025-03-01T00:00:00+08:00",
      "signup_end": "2025-03-10T23:59:59+08:00",
      "start_time": "2025-03-15T09:00:00+08:00",
      "submit_deadline": "2025-03-18T21:00:00+08:00",
      "status": "未开始"
    }
  ]
}
```
- 错误响应：遵循通用约定。

### 旧报名接口弃用说明
- 旧接口：`POST /api/student/competitions/{season_id}/enroll`
- 现行为：统一返回 400，提示“报名需通过队伍”。前端不再直接调用该接口。

### 文档对齐与替换说明
- 初版文档中的“报名赛季：POST `/api/seasons/{seasonId}/signup`”与“`POST /api/student/competitions/{season_id}/enroll`”均已弃用；请使用上述“创建队伍”或“加入队伍”接口完成报名。
- 前端首页 `Home.vue` 渲染“开放报名的竞赛”，点击“报名”跳转到队伍报名页 `/team/enroll?season_id=...`，在该页完成创建或加入队伍；登录采用 `POST /api/auth/student-login` 获取学生 JWT。

### 报名开放判断逻辑
- 满足任一条件即视为开放报名：
  - 当前时间处于报名窗口：`signup_start <= now <= signup_end`
  - 管理员显式开启：`allow_signup = true`
- 公开列表 `GET /api/public/open-competitions` 返回满足上述条件的赛季。

### 管理员创建竞赛：POST `/api/admin/competitions`
- 请求体新增可选字段：
  - `allow_signup`（boolean，默认 `false`）：创建后是否立即开放报名
- 响应新增字段：
  - `allow_signup`（boolean）

### 管理员切换报名开关：POST `/api/admin/competitions/{season_id}/signup-toggle`
- 认证：需要管理员 `Authorization: Bearer <token>`
- 请求体：
```json
{ "allow_signup": true }
```
- 成功响应：
```json
{ "code": 0, "message": "ok", "data": { "season_id": 123, "allow_signup": true } }
```
- 失败响应：
  - 404 竞赛不存在：`{ "code": 1005, "message": "指定的竞赛不存在" }`

## 模块十一：管理员队伍管理（与实现对齐）

说明：以下接口已在后端 `backend/app/routers/admin.py` 中实现，用于管理员查看与维护队伍状态，支持筛选、锁定/解锁、删除队伍、移交队长、移除成员。

### 列出队伍
- GET `/api/admin/teams?season_id?=...&status?=...&locked?=...`
- 认证：需要管理员 `Authorization: Bearer <token>`
- 查询参数（均可选）：
  - `season_id`: 赛季 ID
  - `status`: 队伍状态（示例：`pending|approved|locked`，与系统状态机对齐）
  - `locked`: 是否锁定（true/false）
- 成功响应：
```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "id": 1,
      "name": "队伍A",
      "season_id": 123,
      "captain_id": 10,
      "status": "pending",
      "locked": false,
      "member_count": 3,
      "created_at": "2025-10-05T09:00:00Z"
    }
  ]
}
```

### 锁定队伍
- POST `/api/admin/teams/{team_id}/lock`
- 认证：需要管理员 `Authorization: Bearer <token>`
- 行为：将队伍 `locked` 置为 `true`
- 成功响应：
```json
{ "code": 0, "message": "ok", "data": { "team_id": 1, "locked": true } }
```
- 失败响应：
  - 404 队伍不存在：`{ "code": 1006, "message": "队伍不存在" }`

### 解锁队伍
- POST `/api/admin/teams/{team_id}/unlock`
- 成功响应：
```json
{ "code": 0, "message": "ok", "data": { "team_id": 1, "locked": false } }
```
- 失败响应：同上

### 删除队伍
- POST `/api/admin/teams/{team_id}/delete`
- 行为：删除队伍及其关联的成员、加入令牌、加入请求、提交记录
- 成功响应：
```json
{ "code": 0, "message": "ok", "data": { "team_id": 1, "deleted": true } }
```
- 失败响应：
  - 404 队伍不存在：`{ "code": 1006, "message": "队伍不存在" }`

### 移交队长
- POST `/api/admin/teams/{team_id}/transfer-captain`
- Body：
```json
{ "new_captain_id": 10 }
```
- 行为：将队长更改为现有队伍成员 `students.id = new_captain_id`
- 成功响应：
```json
{ "code": 0, "message": "ok", "data": { "team_id": 1, "captain_id": 10 } }
```
- 失败响应：
  - 404 队伍不存在：`{ "code": 1006, "message": "队伍不存在" }`
  - 400 新队长不在队伍中：`{ "code": 1001, "message": "新队长必须是队伍成员" }`

### 移除成员
- POST `/api/admin/teams/{team_id}/remove-member`
- Body：
```json
{ "student_id": 11 }
```
- 行为：从队伍中移除成员；若为队长则需先移交队长后再移除（接口不允许直接移除队长）
- 成功响应：
```json
{ "code": 0, "message": "ok", "data": { "team_id": 1, "student_id": 11, "removed": true } }
```
- 失败响应：
  - 404 队伍不存在：`{ "code": 1006, "message": "队伍不存在" }`
  - 400 尝试移除队长：`{ "code": 1001, "message": "请先移交队长后再移除" }`

### 说明与约束
- 锁定逻辑：`locked = true` 用于冻结队伍信息，通常在报名截止或队伍审核通过后执行；解锁允许管理员修正。
- 删除队伍为不可逆操作；如需保留审计请在实现层记录操作日志。
- 响应字段与后端实现保持一致；如后续状态机调整，请同步更新文档与前端使用。
