from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from sqlalchemy.orm import Session
from typing import List
import os

from ..db import get_db
from ..models import Season, Team, Submission, SubmissionFile, Review, ReviewScore, Teacher
from ..security import require_teacher, _decode_jwt

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


@router.get("/competitions")
def list_review_competitions(db: Session = Depends(get_db), _: dict = Depends(require_teacher)):
    seasons = db.query(Season).order_by(Season.created_at.desc()).all()
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "submit_deadline": s.submit_deadline.isoformat() if s.submit_deadline else None,
                "review_start": s.review_start.isoformat() if s.review_start else None,
                "review_end": s.review_end.isoformat() if s.review_end else None,
            } for s in seasons
        ]
    }


@router.get("/competitions/{season_id}/submissions")
def list_competition_submissions(season_id: int, db: Session = Depends(get_db), auth: dict = Depends(require_teacher)):
    teacher_account = auth.get("sub")
    teacher = db.query(Teacher).filter(Teacher.account == teacher_account).first()
    if not teacher:
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "令牌无效"})

    teams = db.query(Team).filter(Team.season_id == season_id).all()
    team_ids = [t.id for t in teams]
    subs = db.query(Submission).filter(Submission.team_id.in_(team_ids)).order_by(Submission.uploaded_at.desc()).all()

    # 批量取文件与教师评分状态
    sub_ids = [s.id for s in subs]
    file_map: dict[int, list[SubmissionFile]] = {}
    if sub_ids:
        files = db.query(SubmissionFile).filter(SubmissionFile.submission_id.in_(sub_ids)).all()
        for f in files:
            file_map.setdefault(f.submission_id, []).append(f)

    # 教师是否已评审
    reviewed_map: dict[int, bool] = {}
    if sub_ids:
        rs = db.query(Review).filter(Review.submission_id.in_(sub_ids), Review.teacher_id == teacher.id).all()
        for r in rs:
            reviewed_map[r.submission_id] = True

    def files_to_dto(submission_id: int):
        items = []
        for f in file_map.get(submission_id, []):
            # 仅提供PDF预览下载链接：不暴露材料下载
            preview_url = None
            if f.type == "thesis":
                preview_url = f"/api/teacher/submissions/{submission_id}/files/{f.id}/pdf"
            items.append({
                "id": f.id,
                "type": f.type,
                "filename": f.filename,
                "size": f.size,
                "hash": f.hash,
                "previewUrl": preview_url,
            })
        return items

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": s.id,
                "team_id": s.team_id,
                "version": s.version,
                "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None,
                "files": files_to_dto(s.id),
                "reviewed": bool(reviewed_map.get(s.id, False)),
            } for s in subs
        ]
    }


@router.get("/submissions/{submission_id}/files/{file_id}/pdf")
def preview_submission_pdf(
    submission_id: int,
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = None,
):
    # 允许两种鉴权方式：
    # 1) Authorization: Bearer <jwt>
    # 2) 查询参数 ?token=<jwt>（用于 iframe 不能附带 header 的场景）
    payload = None
    auth_header = request.headers.get("Authorization") if request else None
    if auth_header and auth_header.startswith("Bearer "):
        raw = auth_header.split(" ", 1)[1]
        try:
            payload = _decode_jwt(raw)
        except Exception:
            payload = None
    if payload is None and token:
        try:
            payload = _decode_jwt(token)
        except Exception:
            payload = None
    if not payload or payload.get("role") != "teacher":
        raise HTTPException(status_code=403, detail={"code": 1003, "message": "权限不足：需要教师角色"})

    file = db.query(SubmissionFile).filter(SubmissionFile.id == file_id, SubmissionFile.submission_id == submission_id).first()
    if not file:
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "文件不存在"})
    if file.type != "thesis":
        raise HTTPException(status_code=403, detail={"code": 1003, "message": "仅允许预览论文PDF"})
    if not os.path.exists(file.path):
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "文件不存在或已删除"})

    # 使用 RFC 5987 的 filename* 保持 ASCII，避免非 ASCII 文件名导致头部编码错误
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(file.filename)}",
        "Cache-Control": "no-store",
    }
    return StreamingResponse(open(file.path, "rb"), media_type="application/pdf", headers=headers)


from pydantic import BaseModel, Field

class SubmitScoreBody(BaseModel):
    score: float = Field(description="总分")
    comment: str | None = Field(default=None, description="评语")


@router.post("/submissions/{submission_id}/score")
def submit_score(submission_id: int, body: SubmitScoreBody, db: Session = Depends(get_db), auth: dict = Depends(require_teacher)):
    teacher_account = auth.get("sub")
    teacher = db.query(Teacher).filter(Teacher.account == teacher_account).first()
    if not teacher:
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "令牌无效"})

    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "提交不存在"})

    # 每位教师对一个提交仅保留一条最新评审记录
    review = db.query(Review).filter(Review.submission_id == submission_id, Review.teacher_id == teacher.id).first()
    if not review:
        review = Review(submission_id=submission_id, teacher_id=teacher.id, comment=body.comment)
        db.add(review)
        db.flush()
    else:
        review.comment = body.comment

    # 简化：仅保存一个汇总分维度 total，便于扩展到多维
    score_row = db.query(ReviewScore).filter(ReviewScore.review_id == review.id, ReviewScore.dimension_key == "total").first()
    if not score_row:
        score_row = ReviewScore(review_id=review.id, dimension_key="total", score=body.score)
        db.add(score_row)
    else:
        score_row.score = body.score

    db.commit()

    return {"code": 0, "message": "ok"}