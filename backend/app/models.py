from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(128))


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    college: Mapped[str] = mapped_column(String(64))
    class_name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(128), index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    signup_start: Mapped[DateTime] = mapped_column(DateTime)
    signup_end: Mapped[DateTime] = mapped_column(DateTime)
    start_time: Mapped[DateTime] = mapped_column(DateTime)
    submit_deadline: Mapped[DateTime] = mapped_column(DateTime)
    review_start: Mapped[DateTime] = mapped_column(DateTime)
    review_end: Mapped[DateTime] = mapped_column(DateTime)
    # 报名开关：为 True 时允许报名与公开列表展示（越权于时间窗口）
    allow_signup: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), index=True)  # 未开始/报名中/进行中/评审中/已结束
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    team_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # 内部队伍编号
    name: Mapped[str] = mapped_column(String(128))
    captain_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending/approved/locked
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "student_id", name="uq_team_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="member")  # captain/member
    joined_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class TeamJoinToken(Base):
    __tablename__ = "team_join_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    token: Mapped[str] = mapped_column(String(128), index=True)
    expires_at: Mapped[DateTime] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class TeamJoinRequest(Base):
    __tablename__ = "team_join_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="approved")  # pending/approved/rejected
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class ProblemFile(Base):
    __tablename__ = "problem_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    size: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(128))
    path: Mapped[str] = mapped_column(String(512))
    visible_after_start: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    filename: Mapped[str] = mapped_column(String(256))
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hash: Mapped[str] = mapped_column(String(128))
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))  # thesis | materials
    filename: Mapped[str] = mapped_column(String(256))
    size: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(128))
    path: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class ReviewDimension(Base):
    __tablename__ = "review_dimensions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    key: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(64))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    max_score: Mapped[float] = mapped_column(Float, default=100.0)
    order: Mapped[int] = mapped_column(Integer, default=0)


class ReviewConfig(Base):
    __tablename__ = "review_configs"
    __table_args__ = (
        UniqueConstraint("season_id", name="uq_review_config_season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    require_teacher_count: Mapped[int] = mapped_column(Integer, default=3)
    anonymous_review: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ReviewScore(Base):
    __tablename__ = "review_scores"
    __table_args__ = (
        UniqueConstraint("review_id", "dimension_key", name="uq_review_dimension"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), index=True)
    dimension_key: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(16))  # admin/teacher/student
    actor_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(64))
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class LoginLog(Base):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(16))  # admin/teacher/student
    account: Mapped[str] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("season_id", "student_id", name="uq_enrollment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="approved")  # pending/approved/rejected
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class ExcellentWork(Base):
    __tablename__ = "excellent_works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    # 历年优秀作品可能来自往届或外部文件，允许不绑定队伍或提交
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True, nullable=True)
    submission_id: Mapped[int | None] = mapped_column(ForeignKey("submissions.id"), index=True, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    allow_download: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class ExcellentWorkFile(Base):
    __tablename__ = "excellent_work_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("excellent_works.id"), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    size: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(128))
    path: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text)
    # 发布者（管理员ID，可选）
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True, index=True)
    # 发布时间（由后端写入），显示时区依赖前端格式化
    published_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), index=True)
    # 是否置顶（置顶的公告在列表中优先显示）
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # 创建与更新（审计）
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())