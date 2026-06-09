from fastapi import Header
from app.services.auth_service import verify_token

def get_current_user(
    authorization: str = Header(None)
):
    print("收到token:", authorization)

    if not authorization:
        return None

    user_id = verify_token(
        authorization
    )

    return user_id