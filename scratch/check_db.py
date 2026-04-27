import sqlite3
import os

db_path = 'instance/database.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM user")
    users = cursor.fetchall()
    print("Users in database:")
    for user in users:
        print(user)
    conn.close()
else:
    print("Database not found at", db_path)
