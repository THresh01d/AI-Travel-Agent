from app.database import load_profile
from app.database import load_history


def get_user_profile(user_id):

    profile = load_profile(user_id)

    return profile


def get_user_history(user_id):

    history = load_history(user_id)

    return history