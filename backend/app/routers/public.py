from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import case
from datetime import datetime
import os

from ..db import get_db
from ..models import Season, ExcellentWork, ExcellentWorkFile, Announcement

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/excellent-works")
def list_excellent_works(season_id: int | None = None, limit: int | None = None, db: Session = Depends(get_db)):
    q = db.query(ExcellentWork)
    if season_id:
        q = q.filter(ExcellentWork.season_id == season_id)
    q = q.order_by(ExcellentWork.created_at.desc())
    if limit and limit > 0:
        q = q.limit(limit)
    works = q.all()

    # 批量查询文件列表
    file_map: dict[int, list[ExcellentWorkFile]] = {}
    if works:
        work_ids = [w.id for w in works]
        files = db.query(ExcellentWorkFile).filter(ExcellentWorkFile.work_id.in_(work_ids)).all()
        for f in files:
            file_map.setdefault(f.work_id, []).append(f)

    def to_file_dto(w: ExcellentWork):
        items = []
        for f in file_map.get(w.id, []):
            # 仅当 allow_download 为真时提供下载链接
            download_path = None
            if w.allow_download:
                download_path = f"/api/public/excellent-works/{w.id}/files/{f.id}/download"
            items.append({
                "id": f.id,
                "filename": f.filename,
                "size": f.size,
                "hash": f.hash,
                "downloadUrl": download_path,
            })
        return items

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": w.id,
                "season_id": w.season_id,
                "summary": w.summary,
                "score": w.score,
                "allow_download": w.allow_download,
                "created_at": (w.created_at.isoformat() if w.created_at else None),
                "files": to_file_dto(w),
            }
            for w in works
        ],
    }


@router.get("/excellent-works/{work_id}/files/{file_id}/download")
def download_excellent_file(work_id: int, file_id: int, db: Session = Depends(get_db)):
    work = db.query(ExcellentWork).filter(ExcellentWork.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "优秀作品不存在"})
    if not work.allow_download:
        raise HTTPException(status_code=403, detail={"code": 1003, "message": "该作品不允许下载"})
    file = db.query(ExcellentWorkFile).filter(ExcellentWorkFile.id == file_id, ExcellentWorkFile.work_id == work_id).first()
    if not file:
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "文件不存在"})
    if not os.path.exists(file.path):
        raise HTTPException(status_code=404, detail={"code": 1005, "message": "文件不存在或已删除"})

    headers = {
        "Content-Disposition": f"attachment; filename={file.filename}",
        "Cache-Control": "no-store",
    }
    return StreamingResponse(open(file.path, "rb"), media_type="application/octet-stream", headers=headers)


@router.get("/open-competitions")
def list_open_competitions(db: Session = Depends(get_db)):
    now = datetime.now()
    seasons = (
        db.query(Season)
        .filter(
            (Season.signup_start <= now) & (Season.signup_end >= now) | (Season.allow_signup == True)
        )
        .order_by(Season.signup_start.asc())
        .all()
    )
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "signup_start": s.signup_start.isoformat() if s.signup_start else None,
                "signup_end": s.signup_end.isoformat() if s.signup_end else None,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "submit_deadline": s.submit_deadline.isoformat() if s.submit_deadline else None,
                "status": s.status,
            }
            for s in seasons
        ],
    }


@router.get("/announcements")
def list_announcements(page: int = 1, page_size: int = 3, db: Session = Depends(get_db)):
    # 保护页码与页大小
    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 50))

    # 置顶优先，其次按发布时间倒序；若无发布时间则按创建时间倒序
    q = db.query(Announcement)
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