from datetime import datetime, timedelta, timezone
from jose import jwt
from jose import JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: int) -> str:
    """生成 JWT Token，包含过期时间"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    data = {
        "user_id": user_id,
        "exp": expire,
    }
    token = jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def verify_token(token: str) -> int | None:
    """验证 JWT Token，返回 user_id 或 None"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload["user_id"]
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """把明文密码变成哈希值"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return pwd_context.verify(plain_password, hashed_password)
