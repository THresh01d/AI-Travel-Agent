import pymysql
import os

def get_connection():

    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4"
    )

def save_profile( user_id, profile):

    conn = get_connection()

    cursor = conn.cursor()

    for key, value in profile.items():

        sql = """
        INSERT INTO user_profile
        (user_id, profile_key, profile_value)
        VALUES (%s, %s, %s)
        """

        cursor.execute(
        sql,
        (
            user_id,
            key,
            value
        )
    )

    conn.commit()

    cursor.close()
    conn.close()


def load_profile(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
    SELECT profile_key, profile_value
    FROM user_profile
    WHERE user_id = %s
    """

    cursor.execute(
        sql,
        (user_id,)
    )

    results = cursor.fetchall()

    profile = {}

    for row in results:

        key = row[0]
        value = row[1]

        profile[key] = value

    cursor.close()
    conn.close()

    return profile

def create_user(username, password_hash):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
    INSERT INTO users
    (username, password)
    VALUES (%s, %s)
    """

    cursor.execute(
        sql,
        (username, password_hash)
    )

    conn.commit()

    cursor.close()
    conn.close()

def get_user_by_username(username):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
    SELECT id, username, password
    FROM users
    WHERE username = %s
    """

    cursor.execute(
        sql,
        (username,)
    )

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result

def save_history(
    user_id,
    destination,
    days,
    budget
):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
    INSERT INTO travel_history
    (user_id,destination,days,budget)
    VALUES (%s,%s,%s,%s)
    """

    cursor.execute(
        sql,
        (
            user_id,
            destination,
            days,
            budget
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

def load_history(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
    SELECT
    destination,
    days,
    budget,
    created_time
    FROM travel_history
    WHERE user_id = %s
    ORDER BY created_time DESC
    """

    cursor.execute(
        sql,
        (user_id,)
    )

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return results