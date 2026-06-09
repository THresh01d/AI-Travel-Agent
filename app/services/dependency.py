from fastapi import Depends
from fastapi.security import HTTPBearer
from app.services.auth_service import verify_token

security = HTTPBearer()

def get_current_user(
    credentials = Depends(security)
):
    token = credentials.credentials   # ← FastAPI 自动把 "Bearer xxx" 去掉，只给 token
    print("收到token:", token)
    
    user_id = verify_token(token)
    return user_id
