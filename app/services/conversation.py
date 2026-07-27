
# {user_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
_history: dict[int, list[dict]] = {}


def add_message(user_id: int, role: str, content: str):
    if user_id not in _history:
        _history[user_id] = []

    _history[user_id].append({"role": role, "content": content})

    if len(_history[user_id]) > 10:
        _history[user_id] = _history[user_id][-10:]


def get_history(user_id: int) -> list[dict]:
    return _history.get(user_id, [])
