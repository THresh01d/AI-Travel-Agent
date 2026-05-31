import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)

cursor = conn.cursor()

cursor.execute(
    "SELECT * FROM user_profile"
)

result = cursor.fetchall()

print(result)

cursor.close()
conn.close()