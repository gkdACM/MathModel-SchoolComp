from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import os
import hashlib

from ..db import get_db
from ..models import Student, Season, Enrollment, Team, TeamMember, TeamJoinToken, TeamJoinRequest, Submission, SubmissionFile
from ..security import bearer_scheme, _decode_jwt
from ..config import settings


router = APIRouter(prefix="/api/student", tags=["student"])


def require_student(credentials = Depends(bearer_scheme)):
    payload = _decode_jwt(credentials.credentials)
    if payload.get("role") != "student":
        raise HTTPException(status_code=403, detail={
            "code": 1003,
            "message": "权限不足：需要学生角色",
        })
    return payload


@router.post("/competitions/{season_id}/enroll")
def enroll_competition(season_id: int, db: Session = Depends(get_db), payload: dict = Depends(require_student)):
    # 新流程：需通过创建或加入队伍报名
    raise HTTPException(status_code=400, detail={"code": 2001, "message": "报名需通过队伍：请创建队伍或使用令牌加入队伍"})


def _get_student(payload: dict, db: Session) -> Student:
    student_id_str = payload.get("sub")
    student = db.query(Student).filter(Student.student_id == student_id_str).first()
    if not student or not student.active:
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "学生身份无效"})
    return student


def _signup_open(season: Season) -> bool:
    now = datetime.now()
    window_ok = (season.signup_start and season.signup_end and season.signup_start <= now <= season.signup_end)
    return bool(window_ok or season.allow_signup)


def _find_my_team(db: Session, season_id: int, student_id: int):
    # 查询学生在该赛季是否已有队伍
    return (
        db.query(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .filter(Team.season_id == season_id, TeamMember.student_id == student_id)
        .first()
    )


def _team_response(db: Session, team: Team, include_token: bool = False):
    # 汇总队伍成员
    members = (
        db.query(TeamMember, Student)
        .join(Student, Student.id == TeamMember.student_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    member_list = [{
        "id": s.id,
        "student_id": s.student_id,
        "name": s.name,
        "role": m.role,
    } for m, s in members]

    # 汇总加入请求记录（作为审计/历史）
    reqs = db.query(TeamJoinRequest).filter(TeamJoinRequest.team_id == team.id).order_by(TeamJoinRequest.created_at.desc()).all()
    join_requests = [{
        "id": r.id,
        "student_id": r.student_id,
        "status": r.status,
        "created_at": r.created_at,
    } for r in reqs]

    data = {
        "id": team.id,
        "season_id": team.season_id,
        "team_code": team.team_code,
        "name": team.name,
        "captain_id": team.captain_id,
        "status": team.status,
        "locked": team.locked,
        "members": member_list,
        "join_requests": join_requests,
    }

    if include_token:
        token_row = (
            db.query(TeamJoinToken)
            .filter(TeamJoinToken.team_id == team.id, TeamJoinToken.active == True)
            .order_by(TeamJoinToken.created_at.desc())
            .first()
        )
        if token_row:
            data["join_token"] = {"token": token_row.token, "expires_at": token_row.expires_at}
    return data


@router.post("/competitions/{season_id}/teams")
def create_team_for_season(
    season_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_student),
):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "指定的竞赛不存在"})
    if not _signup_open(season):
        raise HTTPException(status_code=400, detail={"code": 1001, "message": "当前不在报名开放状态"})

    student = _get_student(payload, db)
    # 已有队伍则返回队伍信息
    existing = _find_my_team(db, season_id, student.id)
    if existing:
        return {"code": 0, "message": "ok", "data": _team_response(db, existing, include_token=True)}

    name = (body or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail={"code": 2002, "message": "缺少队伍名称"})

    # 生成队伍编码
    rand = secrets.token_hex(3)  # 6 hex chars
    team_code = f"S{season_id}-{rand}"
    team = Team(season_id=season_id, name=name, captain_id=student.id, team_code=team_code, status="approved")
    db.add(team)
    db.flush()  # 获取 team.id

    # 添加队长成员关系
    db.add(TeamMember(team_id=team.id, student_id=student.id, role="captain"))

    # 自动报名（按学生维度记录）
    exists_enroll = db.query(Enrollment).filter(Enrollment.season_id == season_id, Enrollment.student_id == student.id).first()
    if not exists_enroll:
        db.add(Enrollment(season_id=season_id, student_id=student.id, status="approved"))

    # 默认生成一个加入令牌，7天有效
    token = secrets.token_urlsafe(16)
    expires_at = datetime.now() + timedelta(days=7)
    db.add(TeamJoinToken(team_id=team.id, token=token, expires_at=expires_at, active=True))
    db.commit()
    db.refresh(team)

    return {"code": 0, "message": "ok", "data": _team_response(db, team, include_token=True)}


# ------------------------
# 作品提交（学生）
# ------------------------

def _ensure_member(db: Session, team_id: int, student_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})
    # 成员校验
    rel = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.student_id == student_id)
        .first()
    )
    if not rel:
        raise HTTPException(status_code=403, detail={"code": 1003, "message": "仅队伍成员可提交作品"})
    return team


def _submit_open(season: Season) -> bool:
    now = datetime.now()
    return bool(season.start_time and season.submit_deadline and season.start_time <= now <= season.submit_deadline)


def _sanitize_filename(name: str) -> str:
    # 仅保留中英文、数字与下划线/短横线，其他替换为下划线
    safe = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-"):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe)


@router.post("/teams/{team_id}/submissions")
def upload_submission(
    team_id: int,
    thesis: UploadFile = File(..., description="论文文件（PDF）"),
    materials: UploadFile = File(..., description="支撑材料（RAR/ZIP/7Z）"),
    note: str | None = Form(default=None, description="备注（可选）"),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_student),
):
    # 学生与队伍校验
    student = _get_student(payload, db)
    team = _ensure_member(db, team_id, student.id)

    # 时间窗口校验（开赛至截止）
    season = db.query(Season).filter(Season.id == team.season_id).first()
    if not season or not _submit_open(season):
        raise HTTPException(status_code=400, detail={"code": 1001, "message": "当前不在提交时间窗口内"})

    # 生成自动文件名：队伍名_成员姓名_原始文件名
    members = (
        db.query(TeamMember, Student)
        .join(Student, Student.id == TeamMember.student_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    member_names = [s.name for _, s in members]
    base_name = _sanitize_filename(team.name or f"team_{team.id}")
    names_part = _sanitize_filename("_".join(member_names)) or "members"
    # 文件名与类型校验
    thesis_name_raw = thesis.filename or "thesis.pdf"
    materials_name_raw = materials.filename or "materials.zip"
    thesis_lower = thesis_name_raw.lower()
    materials_lower = materials_name_raw.lower()
    if not thesis_lower.endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"code": 1002, "message": "论文文件类型错误：仅支持 .pdf"})
    if not (materials_lower.endswith(".zip") or materials_lower.endswith(".rar") or materials_lower.endswith(".7z")):
        raise HTTPException(status_code=400, detail={"code": 1003, "message": "支撑材料类型错误：仅支持 .zip/.rar/.7z"})

    thesis_original = _sanitize_filename(thesis_name_raw)
    materials_original = _sanitize_filename(materials_name_raw)
    auto_thesis = f"{base_name}_{names_part}_{thesis_original}"
    auto_materials = f"{base_name}_{names_part}_{materials_original}"

    # 目标路径：uploads/submissions/season_<sid>/team_<tid>/<auto_filename>
    target_rel_dir = os.path.join(settings.submissions_dir, f"season_{team.season_id}", f"team_{team.id}")
    try:
        os.makedirs(target_rel_dir, exist_ok=True)
    except Exception:
        pass
    thesis_rel = os.path.join(target_rel_dir, auto_thesis)
    materials_rel = os.path.join(target_rel_dir, auto_materials)

    # 保存并计算哈希与大小（论文）
    thesis_hasher = hashlib.sha256()
    thesis_size = 0
    with open(thesis_rel, "wb") as out:
        while True:
            chunk = thesis.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            thesis_hasher.update(chunk)
            thesis_size += len(chunk)
    thesis.file.close()

    # 保存并计算哈希与大小（材料）
    materials_hasher = hashlib.sha256()
    materials_size = 0
    with open(materials_rel, "wb") as out:
        while True:
            chunk = materials.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            materials_hasher.update(chunk)
            materials_size += len(chunk)
    materials.file.close()

    # 版本控制：查找当前最大版本并加一
    latest = (
        db.query(Submission)
        .filter(Submission.team_id == team.id)
        .order_by(Submission.version.desc())
        .first()
    )
    next_ver = (latest.version + 1) if latest else 1

    # 总提交记录（将论文作为主文件以兼容旧字段）
    row = Submission(
        team_id=team.id,
        version=next_ver,
        filename=auto_thesis,
        note=note,
        hash=thesis_hasher.hexdigest(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # 关联文件明细
    f_thesis = SubmissionFile(
        submission_id=row.id,
        type="thesis",
        filename=auto_thesis,
        size=thesis_size,
        hash=thesis_hasher.hexdigest(),
        path=thesis_rel,
    )
    f_materials = SubmissionFile(
        submission_id=row.id,
        type="materials",
        filename=auto_materials,
        size=materials_size,
        hash=materials_hasher.hexdigest(),
        path=materials_rel,
    )
    db.add_all([f_thesis, f_materials])
    db.commit()

    return {"code": 0, "message": "ok", "data": {
        "submissionId": row.id,
        "version": row.version,
        "filename": row.filename,
        "uploadedAt": row.uploaded_at,
        "hash": row.hash,
        "files": [
            {"type": "thesis", "filename": f_thesis.filename, "size": f_thesis.size, "hash": f_thesis.hash, "uploadedAt": f_thesis.uploaded_at},
            {"type": "materials", "filename": f_materials.filename, "size": f_materials.size, "hash": f_materials.hash, "uploadedAt": f_materials.uploaded_at},
        ],
    }}


@router.get("/teams/{team_id}/submissions")
def list_submissions(team_id: int, db: Session = Depends(get_db), payload: dict = Depends(require_student)):
    student = _get_student(payload, db)
    team = _ensure_member(db, team_id, student.id)
    rows = (
        db.query(Submission)
        .filter(Submission.team_id == team.id)
        .order_by(Submission.version.asc())
        .all()
    )
    # 加载文件明细
    data = []
    for r in rows:
        files = db.query(SubmissionFile).filter(SubmissionFile.submission_id == r.id).order_by(SubmissionFile.id.asc()).all()
        data.append({
            "id": r.id,
            "version": r.version,
            "filename": r.filename,
            "note": r.note,
            "hash": r.hash,
            "uploadedAt": r.uploaded_at,
            "files": [
                {
                    "type": f.type,
                    "filename": f.filename,
                    "size": f.size,
                    "hash": f.hash,
                    "uploadedAt": f.uploaded_at,
                } for f in files
            ],
        })
    return {"code": 0, "message": "ok", "data": data}


@router.post("/teams/join")
def join_team_by_token(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_student),
):
    token = (body or {}).get("token")
    if not token:
        raise HTTPException(status_code=400, detail={"code": 2003, "message": "缺少加入令牌"})

    token_row = (
        db.query(TeamJoinToken)
        .filter(TeamJoinToken.token == token, TeamJoinToken.active == True)
        .first()
    )
    if not token_row:
        raise HTTPException(status_code=404, detail={"code": 2004, "message": "令牌无效或已过期"})
    if token_row.expires_at and token_row.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail={"code": 2004, "message": "令牌已过期"})

    team = db.query(Team).filter(Team.id == token_row.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})

    season = db.query(Season).filter(Season.id == team.season_id).first()
    if not season or not _signup_open(season):
        raise HTTPException(status_code=400, detail={"code": 1001, "message": "当前不在报名开放状态"})

    student = _get_student(payload, db)
    # 一人一队（同赛季）限制
    existing = _find_my_team(db, team.season_id, student.id)
    if existing:
        # 已在队伍中，返回现有队伍信息
        return {"code": 0, "message": "ok", "data": _team_response(db, existing, include_token=True)}

    # 加入队伍
    db.add(TeamMember(team_id=team.id, student_id=student.id, role="member"))
    # 自动报名（按学生维度记录）
    exists_enroll = db.query(Enrollment).filter(Enrollment.season_id == team.season_id, Enrollment.student_id == student.id).first()
    if not exists_enroll:
        db.add(Enrollment(season_id=team.season_id, student_id=student.id, status="approved"))

    # 记录加入请求（审核历史），当前逻辑直接通过
    db.add(TeamJoinRequest(team_id=team.id, student_id=student.id, status="approved"))
    db.commit()

    return {"code": 0, "message": "ok", "data": _team_response(db, team, include_token=True)}


@router.get("/competitions/{season_id}/my-team")
def get_my_team(season_id: int, db: Session = Depends(get_db), payload: dict = Depends(require_student)):
    student = _get_student(payload, db)
    team = _find_my_team(db, season_id, student.id)
    if not team:
        return {"code": 0, "message": "ok", "data": None}
    return {"code": 0, "message": "ok", "data": _team_response(db, team, include_token=True)}


@router.post("/teams/{team_id}/join-token")
def generate_join_token(team_id: int, db: Session = Depends(get_db), payload: dict = Depends(require_student)):
    student = _get_student(payload, db)
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail={"code": 1006, "message": "队伍不存在"})
    if team.captain_id != student.id:
        raise HTTPException(status_code=403, detail={"code": 1003, "message": "仅队长可生成令牌"})

    # 失效旧令牌
    db.query(TeamJoinToken).filter(TeamJoinToken.team_id == team_id, TeamJoinToken.active == True).update({TeamJoinToken.active: False})
    # 生成新令牌，7天有效
    token = secrets.token_urlsafe(16)
    expires_at = datetime.now() + timedelta(days=7)
    row = TeamJoinToken(team_id=team_id, token=token, expires_at=expires_at, active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"code": 0, "message": "ok", "data": {"token": row.token, "expires_at": row.expires_at}}