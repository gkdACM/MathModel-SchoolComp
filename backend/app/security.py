from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from .config import settings
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# 使用 PBKDF2-SHA256，避免 bcrypt 在当前环境的兼容与长度限制问题
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_jwt(subject: str, role: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.jwt_exp_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


# bearer 令牌解析器
bearer_scheme = HTTPBearer(auto_error=True)


def _decode_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "iss"]},
        )
        if payload.get("iss") != settings.jwt_issuer:
            raise HTTPException(status_code=401, detail={
                "code": 1002,
                "message": "令牌无效：发行者不匹配",
            })
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={
            "code": 1002,
            "message": "令牌已过期",
        })
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={
            "code": 1002,
            "message": "令牌无效",
        })


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """管理员鉴权依赖：解析 Bearer JWT 并要求 role=admin"""
    payload = _decode_jwt(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail={
            "code": 1003,
            "message": "权限不足：需要管理员角色",
        })
    return payload


def require_teacher(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """教师鉴权依赖：解析 Bearer JWT 并要求 role=teacher"""
    payload = _decode_jwt(credentials.credentials)
    if payload.get("role") != "teacher":
        raise HTTPException(status_code=403, detail={
            "code": 1003,
            "message": "权限不足：需要教师角色",
        })
    return payload