from jose import jwt
from jose import JWTError
from passlib.context import CryptContext

SECRET_KEY = "travel_agent_secret"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
"""passlib 自动更新算法"""

ALGORITHM = "HS256"


def create_token(user_id):

    data = {
        "user_id": user_id
    }

    token = jwt.encode(
        data,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def verify_token(token):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
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