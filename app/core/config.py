"""
统一配置 — 所有环境变量在这里集中管理
  - 启动时校验，缺了就报清楚哪个变量没配
  - 用 pydantic-settings 自动从 .env 加载
"""

import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- DeepSeek API ----
    deepseek_api_key: str

    # ---- MySQL ----
    mysql_host: str = "localhost"
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "travel_agent"

    # ---- JWT 认证 ----
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 小时

    # ---- Agent ----
    agent_max_iterations: int = 5

    # ---- 日志 ----
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"  # .env 里有多余变量不报错

settings = Settings()
