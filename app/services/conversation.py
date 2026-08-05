from app.database import get_connection


def add_message(user_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO conversation_messages (user_id, role, content)
        VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (user_id, role, content))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_history(user_id: int, limit: int = 10) -> list[dict]:
    """读取用户最近 limit 条对话，按时间正序返回。

    注意：ORDER BY id DESC 取出来是倒序，
    必须 reversed() 反转成时间正序，否则 Agent 看到的是反的对话。
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql = """
        SELECT role, content
        FROM conversation_messages
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT %s
        """
        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
