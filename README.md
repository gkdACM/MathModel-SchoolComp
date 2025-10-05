# 数学建模校赛网站

一个用于校级数学建模竞赛的全栈网站，支持管理员、教师、学生等角色的竞赛流程管理与信息发布。后端基于 FastAPI + SQLAlchemy + MySQL，前端基于 Vue 3 + Vite。

## 技术栈
- 前端：Vue 3、Vite、Fetch API（或 axios 替代）
- 后端：FastAPI、SQLAlchemy、PyMySQL、Uvicorn
- 数据库：MySQL
- 其他：审计日志记录、鉴权与权限管理、文件上传

## 功能概览
- 管理员
  - 公告管理：分页查询、置顶排序、发布、编辑、删除
  - 队伍/用户管理、竞赛管理、审计日志查询（视项目进展）
- 教师：题目/评审相关功能（视项目进展）
- 学生：参赛报名、提交作品（视项目进展）
- 公共页面：公开公告列表、竞赛信息等

## 项目结构
```
项目根目录
├── backend/                # 后端服务目录
│   ├── app/               # 应用代码：入口、配置、模型、路由、鉴权、审计
│   │   ├── main.py        # FastAPI 应用入口（初始化数据库、注册路由与中间件）
│   │   ├── config.py      # 配置项（数据库、CORS、默认账号等）
│   │   ├── db.py          # 数据库连接与会话管理
│   │   ├── models.py      # ORM 模型（用户、队伍、竞赛、公告、审计等）
│   │   ├── routers/       # 路由模块（管理员、公共接口等）
│   │   └── security.py    # 鉴权与权限依赖
│   ├── requirements.txt   # 后端依赖列表（pip 安装使用）
│   ├── pyproject.toml     # 后端依赖与构建配置
│   └── scripts/           # 脚本（如审计日志导出）
├── frontend/               # 前端工程目录
│   ├── src/               # 源码：入口、路由、视图、API 封装、组件、状态等
│   │   ├── main.js        # 应用入口
│   │   ├── router/        # 路由与导航守卫
│   │   ├── views/         # 视图页面（管理员登录、控制台、公告管理等）
│   │   └── api/           # API 封装（含公告管理与公共接口）
│   ├── vite.config.js     # Vite 开发与构建配置（含 `/api` 代理）
│   └── .env.development   # 开发环境变量（`VITE_API_TARGET` 指向后端）
├── API文档.md              # 接口文档（可用于联调）
├── 前端各个文件的作用.md    # 前端主要文件职责说明
├── 后端各个文件的作用.md    # 后端主要文件职责说明
└── docs/                  # 设计与测试文档（数据库设计、测试账号、用例等）
```

## 快速开始（开发环境）

### 1. 准备依赖
- 安装 Node.js（建议 18+）与 npm
- 安装 Python（建议 3.10+）
- 准备 MySQL 数据库（本地或远程均可）

### 2. 启动后端
1) 安装后端依赖（建议在 `backend/` 目录下运行）：
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) 检查数据库配置：
- 默认在 `backend/app/config.py` 中读取数据库连接；确保 MySQL 可访问且用户具备建库/建表权限。
- 首次启动会自动进行建库/建表与默认数据初始化（包括默认账号）。

3) 启动 FastAPI 服务：
```bash
# 在 backend 目录
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
- 服务地址：`http://localhost:8000`

### 3. 启动前端
1) 安装前端依赖（在 `frontend/` 目录下）：
```bash
cd ../frontend
npm install
```

2) 确认 Vite 代理：
- `frontend/.env.development` 中的 `VITE_API_TARGET` 默认指向 `http://localhost:8000`
- `frontend/src/api/config.js` 默认使用相对路径 `/api` 作为基址，开发时由 Vite 代理到后端

3) 启动前端开发服务器：
```bash
npm run dev
```
- 访问 `http://localhost:5173/`
- 管理员功能入口：参见 `frontend/src/router/index.js`（包含管理员登录、控制台、公告管理等路由）
- 默认管理员账号：请参考 `docs/测试账号.md` 或在 `backend/app/config.py` 中查看/配置

### 4. 联调与验证
- 公告管理页：`/admin/announcements`（受管理员守卫保护）
  - 验证分页查询、置顶排序、发布、编辑、删除是否正常
- 公开公告列表：公共接口路由（参见 `API文档.md` 与 `routers/public.py`）

## 生产部署
- 前端：
  - 构建产物：`npm run build`，生成 `frontend/dist`，建议由 Nginx/静态服务器托管
  - 配置后端地址：通过环境变量 `VITE_API_URL` 指向生产后端，如 `https://your-domain/api`
- 后端：
  - 使用生产级 WSGI/ASGI 服务器（如 `uvicorn` + 进程管理器，或 `gunicorn` + `uvicorn.workers.UvicornWorker`）
  - 数据库连接与 CORS 在 `config.py` 中配置；建议与前端同域（或由反向代理统一域名与路径）
- 反向代理示例（Nginx）：将 `/api` 转发到后端，静态托管 `dist` 目录

## 常见问题
- 端口占用：调整前端端口（Vite 默认 5173）或后端端口（默认 8000）
- CORS 与跨域：开发模式通过 Vite 代理 `/api`；生产建议同域或在后端开启 CORS
- 数据库权限：确保 MySQL 账号拥有建库/建表权限；连接失败时检查 `config.py` 配置
- 排序兼容：MySQL 不支持 `NULLS LAST`，公告排序已使用 `CASE` 适配（见 `routers/admin.py` 与 `routers/public.py`）

## 开发约定
- 新增后端接口：在 `routers/` 中按模块创建，统一鉴权与审计
- 新增数据模型：在 `models.py` 定义并考虑索引与约束；如需初始化默认数据，更新 `main.py` 的启动逻辑
- 新增前端页面：在 `views/` 下创建，并在 `router/index.js` 注册路由与守卫；API 调用统一封装在 `src/api/`
- 环境变量：开发使用 `.env.development` 与 `/api` 代理；生产使用 `VITE_API_URL`

## 文档与参考
- 接口文档：`API文档.md`
- 数据库设计与说明：`docs/数据库设计.md`、`docs/数据库表作用说明.md`
- 测试账号与用例：`docs/测试账号.md`、`docs/测试用例-竞赛管理.md`
- 维护说明：`前端各个文件的作用.md`、`后端各个文件的作用.md`