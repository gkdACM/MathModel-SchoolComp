from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import engine, Base, SessionLocal, ensure_database_exists
from .models import Admin, Student, Teacher
from .security import hash_password
from .routers.auth import router as auth_router
from .routers.admin import router as admin_router
from .routers.public import router as public_router
from .routers.student import router as student_router
from .routers.teacher import router as teacher_router
from .config import settings
import os

app = FastAPI(title="数学建模校赛 API")

# 允许前端开发环境跨域访问（直接请求 http://localhost:8080/api）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    # 确保数据库存在
    ensure_database_exists()
    # 创建表
    Base.metadata.create_all(bind=engine)
    # 简易迁移：为 seasons 增加 allow_signup 列（若不存在）
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'seasons'
                  AND COLUMN_NAME = 'allow_signup'
            """), {"schema": settings.mysql_db})
            cnt = result.scalar() or 0
            if cnt == 0:
                conn.execute(text("ALTER TABLE seasons ADD COLUMN allow_signup TINYINT(1) NOT NULL DEFAULT 0"))
                conn.commit()
    except Exception:
        # 若失败，不阻断启动；后续由运维或 Alembic 处理
        pass

    # 简易迁移：为 teams 增加 team_code 列（若不存在）
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'teams'
                  AND COLUMN_NAME = 'team_code'
            """), {"schema": settings.mysql_db})
            cnt = result.scalar() or 0
            if cnt == 0:
                # 添加可空列，兼容历史数据；由应用在创建队伍时写入值
                conn.execute(text("ALTER TABLE teams ADD COLUMN team_code VARCHAR(32)"))
                # 添加唯一索引以匹配 ORM unique=True（MySQL 允许多个 NULL）
                conn.execute(text("ALTER TABLE teams ADD UNIQUE INDEX uq_teams_team_code (team_code)"))
                conn.commit()
    except Exception:
        # 若失败不阻断启动，避免影响服务可用性
        pass

    # 简易迁移：为 teams 增加 status 与 locked 列（若不存在）
    try:
        with engine.connect() as conn:
            # 检查并添加 status 列
            result_status = conn.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'teams'
                  AND COLUMN_NAME = 'status'
            """), {"schema": settings.mysql_db})
            cnt_status = result_status.scalar() or 0
            if cnt_status == 0:
                conn.execute(text("ALTER TABLE teams ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'pending'"))
                # 与 ORM 一致添加索引
                conn.execute(text("ALTER TABLE teams ADD INDEX idx_teams_status (status)"))

            # 检查并添加 locked 列
            result_locked = conn.execute(text("""
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'teams'
                  AND COLUMN_NAME = 'locked'
            """), {"schema": settings.mysql_db})
            cnt_locked = result_locked.scalar() or 0
            if cnt_locked == 0:
                conn.execute(text("ALTER TABLE teams ADD COLUMN locked TINYINT(1) NOT NULL DEFAULT 0"))
            conn.commit()
    except Exception:
        # 迁移失败不阻断启动，建议后续用 Alembic 正式迁移
        pass
    # 确保上传目录存在
    for d in [settings.upload_base_dir, settings.problems_dir, settings.excellent_dir, settings.submissions_dir]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
    # 初始化默认管理员（账号：root，密码：toor）
    with SessionLocal() as db:  # type: Session
        # 管理员：root/toor
        exists_admin = db.query(Admin).filter(Admin.account == "root").first()
        if not exists_admin:
            admin = Admin(account="root", name="超级管理员", password_hash=hash_password("toor"))
            db.add(admin)

        # 学生测试账号：20230001/123456，邮箱：stu01@example.com
        exists_student = db.query(Student).filter(Student.student_id == "20230001").first()
        if not exists_student:
            stu = Student(
                student_id="20230001",
                name="学生一号",
                college="数学学院",
                class_name="数模2201",
                email="stu01@example.com",
                password_hash=hash_password("123456"),
                active=True,
            )
            db.add(stu)

        # 教师测试账号：t001/123456，邮箱：tea01@example.com
        exists_teacher = db.query(Teacher).filter(Teacher.account == "t001").first()
        if not exists_teacher:
            tea = Teacher(
                account="t001",
                name="教师一号",
                email="tea01@example.com",
                password_hash=hash_password("123456"),
                active=True,
            )
            db.add(tea)

        db.commit()


# 挂载认证与管理员路由
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(public_router)
app.include_router(student_router)
app.include_router(teacher_router)