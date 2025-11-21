# auth.py
import sqlite3
import hashlib
from student import Student

DB_FILE = "auth.db"

class Auth:
    @staticmethod
    def connect():
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def create_table(cls):
        conn = cls.connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL,        -- 'student', 'admin', etc.
                student_id TEXT            -- linked student_id for students
            );
        """)
        conn.commit()
        conn.close()

    @classmethod
    def add_user(cls, username, password, role="student", student_id=None):
        conn = cls.connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO users (username, password, role, student_id)
            VALUES (?, ?, ?, ?)
        """, (username, password, role, student_id))
        conn.commit()
        conn.close()

    @classmethod
    def authenticate(cls, username, password):
        hashed_pw = cls.hash_password(password)
        conn = cls.connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pw))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"username": row["username"], "role": row["role"], "student_id": row["student_id"]}
        return None

    @classmethod
    def get_user(cls, username):
        conn = cls.connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                "username": row["username"],
                "role": row["role"],
                "student_id": row["student_id"]
            }
        return None

    @classmethod
    def delete_user(cls, username):
        conn = cls.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        conn.close()
    @classmethod
    def hash_password(cls, password):
        """Simple SHA-256 hash"""
        return hashlib.sha256(password.encode()).hexdigest()

    @classmethod
    def create_student_account(cls, username, password, name, last_name, email, program, level):
        """
        Create a student account and linked student record
        """
        # 1) Check if username already exists
        if cls.get_user(username):
            return False, "Username already exists."

        # 2) Create student record
        student = Student(username, name, last_name, email, program, level, registered_courses=[] , transcript=[])
        student.save()

        # 3) Create auth user linked to student
        hashed_pw = cls.hash_password(password)
        cls.add_user(username, hashed_pw, role="student", student_id=username)
        return True, f"Account created. Student Username: {username}"
Auth.create_table()
if Auth.get_user("admin") is None:
    Auth.add_user(
        username="admin",
        password=Auth.hash_password("admin123"),
        role="admin",
        student_id=None
    )
    print("Default admin created: username='admin', password='admin123'")

# auto-create table at import
