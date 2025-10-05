from __future__ import annotations
import json
from typing import Any
from sqlalchemy.orm import Session

from .models import AuditLog, Admin, Teacher, Student


def resolve_actor(db: Session, payload: dict) -> tuple[str, int | None, str]:
    """从鉴权载荷解析操作者信息。
    返回 (actor_type, actor_id, actor_account)。若无法解析到ID，返回 None。
    """
    role = payload.get("role") or "admin"
    account = payload.get("sub") or ""

    actor_id: int | None = None
    if role == "admin":
        obj = db.query(Admin).filter(Admin.account == account).first()
        actor_id = obj.id if obj else None
    elif role == "teacher":
        obj = db.query(Teacher).filter(Teacher.account == account).first()
        actor_id = obj.id if obj else None
    elif role == "student":
        obj = db.query(Student).filter(Student.student_id == account).first()
        actor_id = obj.id if obj else None

    return role, actor_id, account


def write_audit_log(
    db: Session,
    actor_type: str,
    actor_id: int | None,
    action: str,
    object_type: str,
    object_id: int | None,
    details: dict[str, Any] | None = None,
) -> None:
    """写入审计日志记录。缺失ID时以0占位，details以JSON字符串保存。"""
    try:
        log = AuditLog(
            actor_type=actor_type,
            actor_id=int(actor_id or 0),
            action=action,
            object_type=object_type,
            object_id=int(object_id or 0),
            details=json.dumps(details or {}, ensure_ascii=False),
        )
        db.add(log)
        db.commit()
    except Exception:
        # 避免因审计失败影响业务流程：吞掉异常，但不回滚业务事务
        db.rollback()
        # 可选：此处未来接入标准日志输出
        pass