import pymysql
from dbutils.pooled_db import PooledDB
from app.core.config import settings

pool = PooledDB(
    creator=pymysql,
    maxconnections=5,
    host=settings.mysql_host,
    user=settings.mysql_user,
    password=settings.mysql_password,
    database=settings.mysql_database,
    charset="utf8mb4",
)


def get_connection():
    return pool.connection()


def save_profile(user_id, profile):
    conn = get_connection()
    cursor = conn.cursor()
    for key, value in profile.items():
        sql = """INSERT INTO user_profile (user_id, profile_key, profile_value) VALUES (%s, %s, %s)"""
        cursor.execute(sql, (user_id, key, value))
    conn.commit()
    cursor.close()
    conn.close()


def load_profile(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    sql = """SELECT profile_key, profile_value FROM user_profile WHERE user_id = %s"""
    cursor.execute(sql, (user_id,))
    results = cursor.fetchall()
    profile = {}
    for row in results:
        profile[row[0]] = row[1]
    cursor.close()
    conn.close()
    return profile


def create_user(username, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO users (username, password) VALUES (%s, %s)"""
    cursor.execute(sql, (username, password_hash))
    conn.commit()
    cursor.close()
    conn.close()


def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    sql = """SELECT id, username, password FROM users WHERE username = %s"""
    cursor.execute(sql, (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def save_history(user_id, destination, days, budget):
    conn = get_connection()
    cursor = conn.cursor()
    sql = """INSERT INTO travel_history (user_id, destination, days, budget) VALUES (%s, %s, %s, %s)"""
    cursor.execute(sql, (user_id, destination, days, budget))
    conn.commit()
    cursor.close()
    conn.close()


def load_history(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    sql = """SELECT destination, days, budget, created_time FROM travel_history
             WHERE user_id = %s ORDER BY created_time DESC"""
    cursor.execute(sql, (user_id,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def init_db():
    """启动时自动建表（幂等：表已存在就不重复建）"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            profile_key VARCHAR(50),
            profile_value TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS travel_history (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            destination VARCHAR(50),
            days INT,
            budget INT,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            role VARCHAR(10),
            content TEXT,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            INDEX idx_user_time (user_id, id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
