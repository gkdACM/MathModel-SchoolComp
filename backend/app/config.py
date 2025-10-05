from pydantic import BaseModel


class Settings(BaseModel):
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "toor"
    mysql_db: str = "math_competition"
    jwt_secret: str = "dev-secret-change-me"
    jwt_issuer: str = "math-modeling-site"
    jwt_exp_minutes: int = 60 * 12
    # 上传目录配置（相对 backend 目录）
    upload_base_dir: str = "uploads"
    problems_dir: str = "uploads/problems"
    excellent_dir: str = "uploads/excellent"
    submissions_dir: str = "uploads/submissions"


settings = Settings()