from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import case

from ..db import get_db
from ..models import Teacher, Season, ProblemFile, ExcellentWork, ExcellentWorkFile, Team, TeamMember, TeamJoinToken, TeamJoinRequest, Submission, Review, ReviewScore, AuditLog, Announcement
from ..security import require_admin, hash_password, verify_password
from ..audit import write_audit_log, resolve_actor
import csv
import io
import os
import hashlib
from datetime import datetime
import json
from ..config import settings


router = APIRouter(prefix="/api/admin", tags=["admin"])


class GenerateTeachersBody(BaseModel):
    names: list[str] = Field(default_factory=list, description="教师中文姓名列表")


@router.post("/teachers/generate")
def generate_teachers(body: GenerateTeachersBody, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    names = [n.strip() for n in body.names if isinstance(n, str) and n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败：names 为空",
            "details": {"fieldErrors": [{"field": "names", "message": "至少提供一个姓名"}]},
        })

    # 读取已有账号并计算当前最大序号（格式 tNNN）
    existing_accounts = [row[0] for row in db.query(Teacher.account).all()]
    max_seq = 0
    for acc in existing_accounts:
        if isinstance(acc, str) and len(acc) >= 2 and acc.startswith("t") and acc[1:].isdigit():
            try:
                n = int(acc[1:])
                if n > max_seq:
                    max_seq = n
            except Exception:
                pass

    rows = []
    created_count = 0
    initial_password = "Math123@123"
    initial_hash = hash_password(initial_password)

    for name in names:
        # 若已存在同名教师，则跳过并返回状态 exists（避免重复创建）
        exists_same_name = db.query(Teacher).filter(Teacher.name == name).first()
        if exists_same_name:
            rows.append({
                "name": name,
                "account": exists_same_name.account,
                "tempPassword": None,
                "status": "exists",
            })
            continue

        # 生成下一个账号：tNNN（三位数，不足左侧补零）
        max_seq += 1
        account = f"t{max_seq:03d}"

        teacher = Teacher(
            account=account,
            name=name,
            email=None,
            password_hash=initial_hash,
            active=True,
        )
        db.add(teacher)
        rows.append({
            "name": name,
            "account": account,
            "tempPassword": initial_password,
            "status": "ok",
        })
        created_count += 1

    if created_count:
        db.commit()
        # 审计：批量生成教师账号
        actor_type, actor_id, _acc = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="teachers.generate",
            object_type="teacher_batch",
            object_id=0,
            details={"created": created_count, "names": names, "rows": rows},
        )

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "rows": rows,
            "created": created_count,
        }
    }


# 创建公告
class CreateAnnouncementBody(BaseModel):
    title: str = Field(description="公告标题")
    content: str = Field(description="公告内容")
    published_at: datetime | None = Field(default=None, description="发布时间（可选，默认当前时间）")
    pinned: bool = Field(default=False, description="是否置顶")


@router.post("/announcements")
def create_announcement(body: CreateAnnouncementBody, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    title = body.title.strip()
    content = body.content.strip()
    if not title:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败：title 为空",
        })
    if not content:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败：content 为空",
        })

    published_at = body.pinned and body.published_at or body.published_at
    # 默认发布时间为当前时间
    if published_at is None:
        published_at = datetime.utcnow()

    # 解析管理员身份用于审计与归属
    actor_type, actor_id, actor_account = resolve_actor(db, _)
    admin_id = None
    if actor_type == "admin":
        # 查询管理员主键ID（Account 在 Admin 表唯一）
        from ..models import Admin
        admin = db.query(Admin).filter(Admin.account == actor_account).first()
        admin_id = admin.id if admin else None

    ann = Announcement(
        title=title,
        content=content,
        admin_id=admin_id,
        published_at=published_at,
        pinned=body.pinned,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)

    # 审计日志
    write_audit_log(
        db,
        actor_type=actor_type,
        actor_id=actor_id,
        action="announcement.create",
        object_type="announcement",
        object_id=ann.id,
        details={"title": title, "pinned": body.pinned, "published_at": published_at.isoformat()},
    )

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "announcement": {
                "id": ann.id,
                "title": ann.title,
                "content": ann.content,
                "publishedAt": ann.published_at.isoformat() if ann.published_at else None,
                "pinned": ann.pinned,
            }
        }
    }


# 管理员分页查询公告列表
@router.get("/announcements")
def list_admin_announcements(page: int = 1, page_size: int = 20, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    # 保护页码与页大小
    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 100))

    # 置顶优先，其次按发布时间倒序；若无发布时间则按创建时间倒序
    q = db.query(Announcement)
    # MySQL 不支持 NULLS LAST，这里用 CASE 将 NULL 放到最后，再按发布时间倒序
    q = q.order_by(
        Announcement.pinned.desc(),
        case((Announcement.published_at == None, 1), else_=0).asc(),
        Announcement.published_at.desc(),
        Announcement.created_at.desc(),
    )
    total = q.count()
    items = (
        q.offset((page - 1) * page_size)
         .limit(page_size)
         .all()
    )

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "rows": [
                {
                    "id": a.id,
                    "title": a.title,
                    "content": a.content,
                    "publishedAt": a.published_at.isoformat() if a.published_at else None,
                    "pinned": a.pinned,
                }
                for a in items
            ],
        },
    }


class UpdateAnnouncementBody(BaseModel):
    title: str | None = Field(default=None, description="公告标题（可选）")
    content: str | None = Field(default=None, description="公告内容（可选）")
    published_at: datetime | None = Field(default=None, description="发布时间（可选）")
    pinned: bool | None = Field(default=None, description="是否置顶（可选）")


@router.post("/announcements/{announcement_id}")
def update_announcement(
    announcement_id: int,
    body: UpdateAnnouncementBody,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "公告不存在"})

    # 应用更新字段
    changed = {}
    if body.title is not None:
        t = body.title.strip()
        if not t:
            raise HTTPException(status_code=400, detail={"code": 1001, "message": "参数校验失败：title 为空"})
        ann.title = t
        changed["title"] = t
    if body.content is not None:
        c = body.content.strip()
        if not c:
            raise HTTPException(status_code=400, detail={"code": 1001, "message": "参数校验失败：content 为空"})
        ann.content = c
        changed["content"] = True
    if body.published_at is not None:
        ann.published_at = body.published_at
        changed["published_at"] = ann.published_at.isoformat() if ann.published_at else None
    if body.pinned is not None:
        ann.pinned = bool(body.pinned)
        changed["pinned"] = ann.pinned

    db.commit()
    db.refresh(ann)

    # 审计日志
    actor_type, actor_id, _ = resolve_actor(db, _)
    write_audit_log(
        db,
        actor_type=actor_type,
        actor_id=actor_id,
        action="announcement.update",
        object_type="announcement",
        object_id=ann.id,
        details=changed,
    )

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "announcement": {
                "id": ann.id,
                "title": ann.title,
                "content": ann.content,
                "publishedAt": ann.published_at.isoformat() if ann.published_at else None,
                "pinned": ann.pinned,
            }
        }
    }


@router.post("/announcements/{announcement_id}/delete")
def delete_announcement(announcement_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail={"code": 404, "message": "公告不存在"})

    db.delete(ann)
    db.commit()

    # 审计日志
    actor_type, actor_id, _ = resolve_actor(db, _)
    write_audit_log(
        db,
        actor_type=actor_type,
        actor_id=actor_id,
        action="announcement.delete",
        object_type="announcement",
        object_id=announcement_id,
        details={"id": announcement_id},
    )

    return {"code": 0, "message": "ok", "data": {"deleted": 1}}


class InitTeacherPasswordsBody(BaseModel):
    accounts: list[str] | None = Field(default=None, description="要重置的教师账号列表")
    all: bool = Field(default=False, description="是否重置所有教师账号")


@router.post("/teachers/password/init")
def init_teacher_passwords(
    body: InitTeacherPasswordsBody,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    # 参数校验：必须 all 为真或提供 accounts 列表
    accounts = [a.strip() for a in (body.accounts or []) if isinstance(a, str) and a.strip()]
    if not body.all and not accounts:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败：请提供 accounts 或设置 all=true",
            "details": {"fieldErrors": [{"field": "accounts|all", "message": "至少提供一个账号或指定重置全部"}]},
        })

    # 选定目标教师
    targets: list[Teacher] = []
    if body.all:
        targets = db.query(Teacher).filter(Teacher.active == True).all()
    else:
        # 按账号查找，不存在的记录返回 not_found
        targets = db.query(Teacher).filter(Teacher.account.in_(accounts)).all()

    default_password = "Math123@123"
    default_hash = hash_password(default_password)

    rows = []
    updated = 0
    found_accounts = {t.account for t in targets}
    # 对已存在的目标批量重置为默认密码
    for t in targets:
        t.password_hash = default_hash
        rows.append({
            "account": t.account,
            "name": t.name,
            "status": "ok",
        })
        updated += 1

    # 标注未找到的账号
    if not body.all and accounts:
        for acc in accounts:
            if acc not in found_accounts:
                rows.append({
                    "account": acc,
                    "name": None,
                    "status": "not_found",
                })

    if updated:
        db.commit()
        # 审计：初始化教师密码
        actor_type, actor_id, _acc = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="teachers.password.init",
            object_type="teacher_batch",
            object_id=0,
            details={"updated": updated, "accounts": accounts, "all": body.all},
        )

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "rows": rows,
            "updated": updated,
            "defaultPassword": default_password,
        }
    }


# ------------------------
# 竞赛管理：创建竞赛与上传赛题 ZIP
# ------------------------

class CreateCompetitionBody(BaseModel):
    name: str = Field(description="竞赛名称")
    start_time: datetime = Field(description="竞赛开始时间（ISO8601）")
    end_time: datetime = Field(description="竞赛结束时间（ISO8601），用于提交截止")
    signup_start: datetime | None = Field(default=None, description="报名开始时间（可选）")
    signup_end: datetime | None = Field(default=None, description="报名结束时间（可选）")
    review_start: datetime | None = Field(default=None, description="评审开始时间（可选）")
    review_end: datetime | None = Field(default=None, description="评审结束时间（可选）")
    allow_signup: bool = Field(default=False, description="是否开放报名（布尔开关）")


@router.post("/competitions")
def create_competition(body: CreateCompetitionBody, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    # 基本校验
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败：name 为空",
            "details": {"fieldErrors": [{"field": "name", "message": "请输入竞赛名称"}]},
        })

    if body.end_time <= body.start_time:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败：结束时间必须晚于开始时间",
            "details": {"fieldErrors": [{"field": "end_time", "message": "结束时间需晚于开始时间"}]},
        })

    # 唯一性校验：名称不能重复
    exists = db.query(Season).filter(Season.name == name).first()
    if exists:
        raise HTTPException(status_code=409, detail={
            "code": 1004,
            "message": "竞赛名称已存在",
            "details": {"fieldErrors": [{"field": "name", "message": "请更换名称"}]},
        })

    season = Season(
        name=name,
        signup_start=body.signup_start or body.start_time,
        signup_end=body.signup_end or body.start_time,
        start_time=body.start_time,
        submit_deadline=body.end_time,
        review_start=body.review_start or body.end_time,
        review_end=body.review_end or body.end_time,
        allow_signup=body.allow_signup,
        status="未开始",
    )
    db.add(season)
    db.commit()
    db.refresh(season)

    # 审计：创建竞赛
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="competition.create",
            object_type="season",
            object_id=season.id,
            details={
                "name": season.name,
                "start_time": season.start_time.isoformat() if season.start_time else None,
                "end_time": season.submit_deadline.isoformat() if season.submit_deadline else None,
                "allow_signup": bool(getattr(season, "allow_signup", False)),
            },
        )
    except Exception:
        pass

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "season": {
                "id": season.id,
                "name": season.name,
                "start_time": season.start_time.isoformat(),
                "end_time": season.submit_deadline.isoformat(),
                "status": season.status,
            }
        }
    }

# 报名开关：管理员可切换 allow_signup
class ToggleSignupBody(BaseModel):
    allow_signup: bool = Field(description="是否开放报名")


@router.post("/competitions/{season_id}/signup-toggle")
def toggle_competition_signup(
    season_id: int,
    body: ToggleSignupBody,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail={
            "code": 1005,
            "message": "指定的竞赛不存在",
        })
    season.allow_signup = body.allow_signup
    db.add(season)
    db.commit()
    db.refresh(season)

    # 审计：切换报名开关
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="competition.signup_toggle",
            object_type="season",
            object_id=season.id,
            details={"allow_signup": bool(season.allow_signup)},
        )
    except Exception:
        pass
    return {
        "code": 0,
        "message": "ok",
        "data": {"season_id": season.id, "allow_signup": season.allow_signup},
    }

@router.get("/competitions")
def list_competitions(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    seasons = db.query(Season).order_by(Season.created_at.desc()).all()
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.submit_deadline.isoformat() if s.submit_deadline else None,
                "status": s.status,
                "allow_signup": bool(getattr(s, "allow_signup", False)),
            }
            for s in seasons
        ]
    }


@router.post("/competitions/{season_id}/problems/upload")
def upload_competition_zip(
    season_id: int,
    file: UploadFile = File(..., description="ZIP 压缩包"),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    # 存在性校验
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail={
            "code": 1005,
            "message": "指定的竞赛不存在",
        })

    # 仅允许 zip 文件
    filename = file.filename or "problems.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "文件类型错误：仅支持 .zip",
        })

    # 目标文件路径（覆盖保存）
    target_rel = os.path.join(settings.problems_dir, f"season_{season_id}.zip")
    target_rel_dir = os.path.dirname(target_rel)
    try:
        os.makedirs(target_rel_dir, exist_ok=True)
    except Exception:
        pass

    # 保存并计算哈希与大小
    hasher = hashlib.sha256()
    size = 0
    with open(target_rel, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            hasher.update(chunk)
            size += len(chunk)
    file.file.close()

    # 更新或创建记录
    pf = db.query(ProblemFile).filter(ProblemFile.season_id == season_id).first()
    existed = bool(pf)
    if pf:
        pf.filename = filename
        pf.size = size
        pf.hash = hasher.hexdigest()
        pf.path = target_rel
        # visible_after_start 保持默认不变
    else:
        pf = ProblemFile(
            season_id=season_id,
            filename=filename,
            size=size,
            hash=hasher.hexdigest(),
            path=target_rel,
            visible_after_start=True,
        )
        db.add(pf)
    db.commit()

    # 审计：上传题目ZIP
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="problems.upload",
            object_type="season",
            object_id=season_id,
            details={
                "filename": filename,
                "size": size,
                "hash": pf.hash,
                "path": pf.path,
                "updated": existed,
            },
        )
    except Exception:
        pass

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "season_id": season_id,
            "filename": filename,
            "size": size,
            "hash": pf.hash,
            "path": pf.path,
            "uploaded_at": (pf.uploaded_at.isoformat() if pf.uploaded_at else None),
        }
    }


# ------------------------
# 历年优秀作品：管理员上传文件与元数据
# ------------------------

@router.post("/competitions/{season_id}/excellent/upload")
def upload_excellent_work(
    season_id: int,
    file: UploadFile = File(..., description="优秀作品文件（ZIP/PDF）"),
    summary: str | None = Form(default=None, description="作品摘要（可选）"),
    score: float | None = Form(default=None, description="评分（可选）"),
    allow_download: bool = Form(default=False, description="是否允许下载"),
    team_id: int | None = Form(default=None, description="关联队伍ID（可选）"),
    submission_id: int | None = Form(default=None, description="关联提交ID（可选）"),
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    # 校验赛季存在
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail={
            "code": 1005,
            "message": "指定的竞赛不存在",
        })

    # 限制文件类型（允许 zip/pdf）
    filename = file.filename or "excellent.zip"
    lower = filename.lower()
    if not (lower.endswith(".zip") or lower.endswith(".pdf")):
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "文件类型错误：仅支持 .zip 或 .pdf",
        })

    # 查找或创建 ExcellentWork（若提供 team_id 或 submission_id 则尝试复用）
    work = None
    if team_id or submission_id:
        q = db.query(ExcellentWork).filter(ExcellentWork.season_id == season_id)
        if team_id:
            q = q.filter(ExcellentWork.team_id == team_id)
        if submission_id:
            q = q.filter(ExcellentWork.submission_id == submission_id)
        work = q.first()

    if not work:
        work = ExcellentWork(
            season_id=season_id,
            team_id=team_id,
            submission_id=submission_id,
            summary=summary,
            score=score,
            allow_download=allow_download or False,
        )
        db.add(work)
        db.commit()
        db.refresh(work)
        # 审计：创建优秀作品条目
        try:
            actor_type, actor_id, _account = resolve_actor(db, _)
            write_audit_log(
                db,
                actor_type=actor_type,
                actor_id=actor_id,
                action="excellent_work.upsert",
                object_type="excellent_work",
                object_id=work.id,
                details={
                    "op": "create",
                    "season_id": season_id,
                    "team_id": team_id,
                    "submission_id": submission_id,
                    "summary": summary,
                    "score": score,
                    "allow_download": bool(allow_download),
                },
            )
        except Exception:
            pass
    else:
        # 更新元信息（若传入）
        if summary is not None:
            work.summary = summary
        if score is not None:
            work.score = score
        work.allow_download = bool(allow_download)
        if team_id:
            work.team_id = team_id
        if submission_id:
            work.submission_id = submission_id
        db.commit()
        # 审计：更新优秀作品条目
        try:
            actor_type, actor_id, _account = resolve_actor(db, _)
            write_audit_log(
                db,
                actor_type=actor_type,
                actor_id=actor_id,
                action="excellent_work.upsert",
                object_type="excellent_work",
                object_id=work.id,
                details={
                    "op": "update",
                    "season_id": season_id,
                    "team_id": team_id,
                    "submission_id": submission_id,
                    "summary": work.summary,
                    "score": work.score,
                    "allow_download": bool(work.allow_download),
                },
            )
        except Exception:
            pass

    # 准备目录：uploads/excellent/season_{season_id}/work_{work.id}/
    dir_rel = os.path.join(settings.excellent_dir, f"season_{season_id}", f"work_{work.id}")
    try:
        os.makedirs(dir_rel, exist_ok=True)
    except Exception:
        pass

    target_rel = os.path.join(dir_rel, filename)

    # 保存文件并计算哈希与大小
    hasher = hashlib.sha256()
    size = 0
    with open(target_rel, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            hasher.update(chunk)
            size += len(chunk)
    file.file.close()

    # 记录文件元数据
    wf = ExcellentWorkFile(
        work_id=work.id,
        filename=filename,
        size=size,
        hash=hasher.hexdigest(),
        path=target_rel,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)

    # 审计：上传优秀作品文件
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="excellent_work.file_upload",
            object_type="excellent_work_file",
            object_id=wf.id,
            details={
                "work_id": work.id,
                "filename": filename,
                "size": size,
                "hash": wf.hash,
                "path": wf.path,
            },
        )
    except Exception:
        pass

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "work_id": work.id,
            "season_id": season_id,
            "filename": filename,
            "size": size,
            "hash": wf.hash,
            "path": wf.path,
            "uploaded_at": (wf.uploaded_at.isoformat() if wf.uploaded_at else None),
            "summary": work.summary,
            "score": work.score,
            "allow_download": work.allow_download,
        }
    }


@router.get("/teachers/password/export")
def export_teacher_passwords(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    # 导出CSV：account,name,password
    # 若教师当前密码仍为默认密码，则导出默认密码；否则留空，避免泄露
    default_password = "Math123@123"
    teachers = db.query(Teacher).order_by(Teacher.account.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["account", "name", "password"])  # 表头
    for t in teachers:
        pwd = default_password if verify_password(default_password, t.password_hash) else ""
        writer.writerow([t.account or "", t.name or "", pwd])

    buf.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=teachers-passwords.csv",
        "Cache-Control": "no-store",
    }
    # 审计：导出教师密码（仅导出默认密码）
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        defaults_count = sum(1 for t in teachers if verify_password(default_password, t.password_hash))
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="teachers.password_export",
            object_type="teacher",
            object_id=0,
            details={
                "total_teachers": len(teachers),
                "default_password_count": defaults_count,
            },
        )
    except Exception:
        pass
    return StreamingResponse(buf, media_type="text/csv", headers=headers)

# ------------------------
# 管理员：导出当前赛季成绩表（CSV）
# ------------------------

@router.get("/competitions/{season_id}/scores/export")
def export_current_scores(
    season_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """
    导出按队伍聚合的成绩表：
    表头为：队伍, 学生1, 学生2, 学生3, 分数
    分数为该队伍最新提交的所有教师评分（维度 total）的平均分。
    """
    # 获取赛季内队伍
    teams = db.query(Team).filter(Team.season_id == season_id).all()
    team_ids = [t.id for t in teams]

    # 预取所有队伍的提交，用于选择“最新提交”
    subs_by_team: dict[int, list[Submission]] = {tid: [] for tid in team_ids}
    if team_ids:
        all_subs = (
            db.query(Submission)
            .filter(Submission.team_id.in_(team_ids))
            .order_by(Submission.uploaded_at.asc())
            .all()
        )
        for s in all_subs:
            subs_by_team.setdefault(s.team_id, []).append(s)

    # 预取队伍成员与学生姓名（按队长优先，其次加入时间），最多三人
    from ..models import Student  # 延迟导入以避免循环
    members_map: dict[int, list[str]] = {tid: [] for tid in team_ids}
    if team_ids:
        tm_rows = (
            db.query(TeamMember)
            .filter(TeamMember.team_id.in_(team_ids))
            .order_by(TeamMember.joined_at.asc())
            .all()
        )
        # 收集涉及的学生ID
        stu_ids = {tm.student_id for tm in tm_rows}
        students = []
        if stu_ids:
            students = db.query(Student).filter(Student.id.in_(list(stu_ids))).all()
        stu_name_map = {stu.id: (stu.name or "") for stu in students}
        # 构建每队成员列表（队长优先）
        by_team: dict[int, list[TeamMember]] = {}
        for tm in tm_rows:
            by_team.setdefault(tm.team_id, []).append(tm)
        for tid, tms in by_team.items():
            # 队长优先，其次加入时间
            tms_sorted = sorted(tms, key=lambda x: (0 if x.role == "captain" else 1, x.joined_at))
            names = []
            for tm in tms_sorted[:3]:
                names.append(stu_name_map.get(tm.student_id, ""))
            members_map[tid] = names

    # 计算每队最新提交的平均分（维度 total）
    def pick_latest(subs: list[Submission]) -> Submission | None:
        if not subs:
            return None
        # 以上传时间为主，其次版本号，其次ID
        return sorted(
            subs,
            key=lambda s: (
                s.uploaded_at or datetime.min,
                s.version or 0,
                s.id,
            ),
            reverse=True,
        )[0]

    avg_map: dict[int, float | str] = {}
    for tid in team_ids:
        latest = pick_latest(subs_by_team.get(tid, []))
        if not latest:
            avg_map[tid] = ""
            continue
        # 收集对应提交的所有评审与总分
        reviews = db.query(Review).filter(Review.submission_id == latest.id).all()
        if not reviews:
            avg_map[tid] = ""
            continue
        review_ids = [r.id for r in reviews]
        score_rows = (
            db.query(ReviewScore)
            .filter(ReviewScore.review_id.in_(review_ids), ReviewScore.dimension_key == "total")
            .all()
        )
        scores = [sr.score for sr in score_rows if sr.score is not None]
        avg_map[tid] = round(sum(scores) / len(scores), 4) if scores else ""

    # 输出 CSV（添加 BOM 以便 Excel 正常识别 UTF-8）
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow(["队伍", "学生1", "学生2", "学生3", "分数"])
    for t in teams:
        names = members_map.get(t.id, [])
        # 保证长度为3
        col_students = [(names[0] if len(names) > 0 else ""), (names[1] if len(names) > 1 else ""), (names[2] if len(names) > 2 else "")]
        writer.writerow([t.name or "", *col_students, avg_map.get(t.id, "")])

    buf.seek(0)
    fname = f"scores-season-{season_id}-teams.csv"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}",
        "Cache-Control": "no-store",
    }
    # 审计：导出赛季成绩
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="scores.export",
            object_type="season",
            object_id=season_id,
            details={
                "team_count": len(teams),
                "file_name": fname,
                "dimension": "total",
            },
        )
    except Exception:
        pass
    return StreamingResponse(buf, media_type="text/csv", headers=headers)

# ------------------------
# 管理员：统计还未完成评分的教师（按赛季）
# ------------------------

@router.get("/competitions/{season_id}/reviews/progress")
def teacher_review_progress(
    season_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    teams = db.query(Team).filter(Team.season_id == season_id).all()
    team_ids = [t.id for t in teams]
    submissions = []
    if team_ids:
        submissions = db.query(Submission).filter(Submission.team_id.in_(team_ids)).all()
    sub_ids = [s.id for s in submissions]
    total = len(sub_ids)

    # 全部激活的教师
    teachers = db.query(Teacher).filter(Teacher.active == True).order_by(Teacher.account.asc()).all()

    progress = []
    if total == 0:
        # 若没有提交，则默认全部完成（避免除零）
        for t in teachers:
            progress.append({
                "teacher_id": t.id,
                "account": t.account,
                "name": t.name,
                "total_submissions": total,
                "reviewed_count": 0,
                "pending_count": 0,
                "completion_rate": 100.0,
            })
    else:
        for t in teachers:
            reviewed_count = db.query(Review).filter(Review.submission_id.in_(sub_ids), Review.teacher_id == t.id).count()
            pending_count = max(total - reviewed_count, 0)
            completion_rate = round(reviewed_count / total * 100.0, 2)
            progress.append({
                "teacher_id": t.id,
                "account": t.account,
                "name": t.name,
                "total_submissions": total,
                "reviewed_count": reviewed_count,
                "pending_count": pending_count,
                "completion_rate": completion_rate,
            })

    # 返回未完成的教师列表与总体统计
    uncompleted = [p for p in progress if p.get("pending_count", 0) > 0]
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "season_id": season_id,
            "total_submissions": total,
            "teachers": progress,
            "uncompleted": uncompleted,
        }
    }

# ------------------------
# 管理员：队伍管理
# ------------------------

class ListTeamsQuery(BaseModel):
    season_id: int | None = Field(default=None, description="赛季ID（可选）")
    status: str | None = Field(default=None, description="队伍状态 pending/approved/locked（可选）")
    locked: bool | None = Field(default=None, description="是否锁定（可选）")


@router.get("/teams")
def list_teams(
    season_id: int | None = None,
    status: str | None = None,
    locked: bool | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    q = db.query(Team)
    if season_id is not None:
        q = q.filter(Team.season_id == season_id)
    if status:
        q = q.filter(Team.status == status)
    if locked is not None:
        q = q.filter(Team.locked == locked)
    teams = q.order_by(Team.created_at.desc()).all()

    def team_info(t: Team):
        member_count = db.query(TeamMember).filter(TeamMember.team_id == t.id).count()
        return {
            "id": t.id,
            "season_id": t.season_id,
            "team_code": t.team_code,
            "name": t.name,
            "captain_id": t.captain_id,
            "status": t.status,
            "locked": t.locked,
            "member_count": member_count,
            "created_at": t.created_at,
        }

    return {"code": 0, "message": "ok", "data": [team_info(t) for t in teams]}


@router.post("/teams/{team_id}/lock")
def lock_team(team_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})
    before_locked = bool(team.locked)
    team.locked = True
    team.status = "locked"
    db.add(team)
    db.commit()
    db.refresh(team)
    # 审计：锁定队伍
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="team.lock",
            object_type="team",
            object_id=team.id,
            details={"before_locked": before_locked, "after_locked": True, "status": team.status},
        )
    except Exception:
        pass
    return {"code": 0, "message": "ok", "data": {"team_id": team.id, "locked": team.locked, "status": team.status}}


@router.post("/teams/{team_id}/unlock")
def unlock_team(team_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})
    before_locked = bool(team.locked)
    team.locked = False
    team.status = "approved"
    db.add(team)
    db.commit()
    db.refresh(team)
    # 审计：解锁队伍
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="team.unlock",
            object_type="team",
            object_id=team.id,
            details={"before_locked": before_locked, "after_locked": False, "status": team.status},
        )
    except Exception:
        pass
    return {"code": 0, "message": "ok", "data": {"team_id": team.id, "locked": team.locked, "status": team.status}}


@router.post("/teams/{team_id}/delete")
def delete_team(team_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})

    db.query(TeamMember).filter(TeamMember.team_id == team_id).delete(synchronize_session=False)
    db.query(TeamJoinToken).filter(TeamJoinToken.team_id == team_id).delete(synchronize_session=False)
    db.query(TeamJoinRequest).filter(TeamJoinRequest.team_id == team_id).delete(synchronize_session=False)
    db.query(Submission).filter(Submission.team_id == team_id).delete(synchronize_session=False)

    db.delete(team)
    db.commit()
    # 审计：删除队伍
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="team.delete",
            object_type="team",
            object_id=team_id,
            details={
                "name": team.name,
                "team_code": team.team_code,
                "season_id": team.season_id,
            },
        )
    except Exception:
        pass
    return {"code": 0, "message": "ok", "data": {"team_id": team_id, "deleted": True}}


class TransferCaptainBody(BaseModel):
    new_captain_id: int = Field(description="新队长的学生主键ID（students.id）")


@router.post("/teams/{team_id}/transfer-captain")
def transfer_captain(team_id: int, body: TransferCaptainBody, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})

    new_id = body.new_captain_id
    new_member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.student_id == new_id).first()
    if not new_member:
        raise HTTPException(status_code=400, detail={"code": 2007, "message": "新队长必须是当前队伍成员"})

    old_captain_member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.student_id == team.captain_id).first()
    if old_captain_member:
        old_captain_member.role = "member"
        db.add(old_captain_member)

    new_member.role = "captain"
    team.captain_id = new_id
    db.add(new_member)
    db.add(team)
    db.commit()
    db.refresh(team)

    # 审计：转移队长
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="team.transfer_captain",
            object_type="team",
            object_id=team.id,
            details={"old_captain_id": old_captain_member.student_id if old_captain_member else None, "new_captain_id": body.new_captain_id},
        )
    except Exception:
        pass

    return {"code": 0, "message": "ok", "data": {"team_id": team.id, "captain_id": team.captain_id}}


class RemoveMemberBody(BaseModel):
    student_id: int = Field(description="要移除成员的学生主键ID（students.id）")


@router.post("/teams/{team_id}/remove-member")
def remove_member(team_id: int, body: RemoveMemberBody, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})

    if body.student_id == team.captain_id:
        raise HTTPException(status_code=400, detail={"code": 2008, "message": "不可直接移除队长，请先转移队长"})

    member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.student_id == body.student_id).first()
    if not member:
        raise HTTPException(status_code=404, detail={"code": 2009, "message": "成员不在该队伍中"})

    db.delete(member)
    db.commit()
    # 审计：移除队员
    try:
        actor_type, actor_id, _account = resolve_actor(db, _)
        write_audit_log(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            action="team.remove_member",
            object_type="team",
            object_id=team_id,
            details={"student_id": body.student_id},
        )
    except Exception:
        pass
    return {"code": 0, "message": "ok", "data": {"team_id": team_id, "student_id": body.student_id, "removed": True}}

# ------------------------
# 审计日志查询与导出接口
# ------------------------

@router.get("/audit/logs")
def list_audit_logs(
    actor_type: str | None = None,
    actor_id: int | None = None,
    action: str | None = None,
    object_type: str | None = None,
    object_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    q = db.query(AuditLog)
    if actor_type:
        q = q.filter(AuditLog.actor_type == actor_type)
    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if object_type:
        q = q.filter(AuditLog.object_type == object_type)
    if object_id is not None:
        q = q.filter(AuditLog.object_id == object_id)
    if start_time is not None:
        q = q.filter(AuditLog.created_at >= start_time)
    if end_time is not None:
        q = q.filter(AuditLog.created_at <= end_time)

    total = q.count()
    q = q.order_by(AuditLog.created_at.desc())
    items = q.offset(max(0, (page - 1) * page_size)).limit(page_size).all()

    def to_dict(row: AuditLog):
        try:
            details = json.loads(row.details or "{}")
        except Exception:
            details = {}
        return {
            "id": row.id,
            "actor_type": row.actor_type,
            "actor_id": row.actor_id,
            "action": row.action,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "details": details,
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
        }

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": [to_dict(x) for x in items],
        },
    }


@router.get("/audit/logs/export")
def export_audit_logs(
    actor_type: str | None = None,
    actor_id: int | None = None,
    action: str | None = None,
    object_type: str | None = None,
    object_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    q = db.query(AuditLog)
    if actor_type:
        q = q.filter(AuditLog.actor_type == actor_type)
    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if object_type:
        q = q.filter(AuditLog.object_type == object_type)
    if object_id is not None:
        q = q.filter(AuditLog.object_id == object_id)
    if start_time is not None:
        q = q.filter(AuditLog.created_at >= start_time)
    if end_time is not None:
        q = q.filter(AuditLog.created_at <= end_time)

    rows = q.order_by(AuditLog.created_at.desc()).all()

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM for Excel
    writer = csv.writer(buf)
    writer.writerow(["id", "created_at", "actor_type", "actor_id", "action", "object_type", "object_id", "details"])  # header
    for r in rows:
        writer.writerow([
            r.id,
            (r.created_at.isoformat() if getattr(r, "created_at", None) else ""),
            r.actor_type,
            r.actor_id,
            r.action,
            r.object_type,
            r.object_id,
            (r.details or "{}"),
        ])
    buf.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=audit-logs.csv",
        "Cache-Control": "no-store",
    }
    return StreamingResponse(buf, media_type="text/csv", headers=headers)