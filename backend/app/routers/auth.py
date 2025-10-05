from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Admin, Student, Teacher
from ..security import verify_password, create_jwt


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    account: str
    password: str


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    account = body.account.strip()
    admin = db.query(Admin).filter(Admin.account == account).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail={
            "code": 1002,
            "message": "账号或密码错误",
        })

    token = create_jwt(subject=admin.account, role="admin")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "token": token,
            "role": "admin",
            "profile": {
                "account": admin.account,
                "name": admin.name,
            }
        }
    }


# 管理员专用登录接口：/api/auth/adminManager-login
@router.post("/adminManager-login")
def admin_manager_login(body: LoginBody, db: Session = Depends(get_db)):
    account = body.account.strip()
    admin = db.query(Admin).filter(Admin.account == account).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail={
            "code": 1002,
            "message": "账号或密码错误",
        })

    token = create_jwt(subject=admin.account, role="admin")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "token": token,
            "role": "admin",
            "profile": {
                "account": admin.account,
                "name": admin.name,
            }
        }
    }


# 学生登录接口：/api/auth/student-login
class StudentLoginBody(BaseModel):
    studentId: str | None = None
    email: str | None = None
    password: str


@router.post("/student-login")
def student_login(body: StudentLoginBody, db: Session = Depends(get_db)):
    identifier = (body.studentId or "").strip()
    email = (body.email or "").strip()

    if not identifier and not email:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "缺少登录标识：studentId 或 email",
        })

    student = None
    if identifier:
        student = db.query(Student).filter(Student.student_id == identifier).first()
    elif email:
        student = db.query(Student).filter(Student.email == email).first()

    if not student or not student.active or not verify_password(body.password, student.password_hash):
        raise HTTPException(status_code=401, detail={
            "code": 1002,
            "message": "账号或密码错误",
        })

    token = create_jwt(subject=student.student_id, role="student")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "token": token,
            "role": "student",
            "profile": {
                "studentId": student.student_id,
                "name": student.name,
                "email": student.email,
            }
        }
    }


# 教师登录接口：/api/auth/teacher-login
class TeacherLoginBody(BaseModel):
    account: str
    password: str


@router.post("/teacher-login")
def teacher_login(body: TeacherLoginBody, db: Session = Depends(get_db)):
    account = body.account.strip()
    teacher = db.query(Teacher).filter(Teacher.account == account).first()
    if not teacher or not teacher.active or not verify_password(body.password, teacher.password_hash):
        raise HTTPException(status_code=401, detail={
            "code": 1002,
            "message": "账号或密码错误",
        })

    token = create_jwt(subject=teacher.account, role="teacher")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "token": token,
            "role": "teacher",
            "profile": {
                "account": teacher.account,
                "name": teacher.name,
                "email": teacher.email,
            }
        }
    }


# 学生注册接口：/api/auth/student/register
class StudentRegisterBody(BaseModel):
    studentId: str
    name: str
    college: str
    # 文档字段为 "class"，此处用别名映射到后端的 class_name
    class_name: str
    email: str
    password: str


@router.post("/student/register")
def student_register(body: StudentRegisterBody, db: Session = Depends(get_db)):
    sid = body.studentId.strip()
    name = body.name.strip()
    college = body.college.strip()
    class_name = body.class_name.strip()
    email = body.email.strip()
    password = body.password

    # 基本校验
    field_errors = []
    if not sid:
        field_errors.append({"field": "studentId", "message": "学号不能为空"})
    if not name:
        field_errors.append({"field": "name", "message": "姓名不能为空"})
    if not college:
        field_errors.append({"field": "college", "message": "学院不能为空"})
    if not class_name:
        field_errors.append({"field": "class", "message": "班级不能为空"})
    if not email or "@" not in email:
        field_errors.append({"field": "email", "message": "邮箱格式不正确"})
    if not password or len(password) < 6:
        field_errors.append({"field": "password", "message": "密码至少6位"})

    if field_errors:
        raise HTTPException(status_code=400, detail={
            "code": 1001,
            "message": "参数校验失败",
            "details": {"fieldErrors": field_errors},
        })

    # 学号唯一性检查
    exists = db.query(Student).filter(Student.student_id == sid).first()
    if exists:
        raise HTTPException(status_code=409, detail={
            "code": 1007,
            "message": "学号已注册",
            "details": {"fieldErrors": [{"field": "studentId", "message": "该学号已存在"}]},
        })

    # 可选：邮箱重复提示（不强制唯一）
    # email_exists = db.query(Student).filter(Student.email == email).first()
    # if email_exists:
    #     raise HTTPException(status_code=409, detail={
    #         "code": 1007,
    #         "message": "邮箱已注册",
    #         "details": {"fieldErrors": [{"field": "email", "message": "该邮箱已存在"}]},
    #     })

    from ..security import hash_password
    s = Student(
        student_id=sid,
        name=name,
        college=college,
        class_name=class_name,
        email=email,
        password_hash=hash_password(password),
        active=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    return {"code": 0, "message": "ok"}