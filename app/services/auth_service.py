from jose import jwt
from jose import JWTError

SECRET_KEY = "travel_agent_secret"

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