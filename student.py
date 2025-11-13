
import sqlite3

class Student:
    def __init__(self, student_id, name, last_name, email, program, level, transcript=None):
        self.student_id = student_id
        self.name = name
        self.last_name = last_name
        self.email = email
        self.program = program
        self.level = level
        self.transcript = transcript or []   # list of course codes

    # -----------------------------
    # Database Connection
    # -----------------------------
    @staticmethod
    def connect():
        conn = sqlite3.connect("students.db")
        conn.row_factory = sqlite3.Row
        return conn

    # -----------------------------
    # CREATE TABLE
    # -----------------------------
    @classmethod
    def create_table(cls):
        conn = cls.connect()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                last_name  TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                program    TEXT NOT NULL,
                level      INTEGER NOT NULL,
                transcript TEXT
            );
        """)

        conn.commit()
        conn.close()

    # -----------------------------
    # SAVE STUDENT (Insert / Update)
    # -----------------------------
    def save(self):
        conn = Student.connect()
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO students
            (student_id, name, last_name, email, program, level, transcript)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.student_id, self.name, self.last_name,
            self.email, self.program, self.level,
            ",".join(self.transcript)
        ))

        conn.commit()
        conn.close()

    # -----------------------------
    # GET STUDENT BY ID
    # -----------------------------
    @classmethod
    def get(cls, student_id):
        conn = cls.connect()
        cur = conn.cursor()

        cur.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        row = cur.fetchone()

        conn.close()

        if row:
            transcript_list = row["transcript"].split(",") if row["transcript"] else []
            return Student(
                row["student_id"],
                row["name"],
                row["last_name"],
                row["email"],
                row["program"],
                row["level"],
                transcript_list
            )

        return None

    # -----------------------------
    # DELETE STUDENT
    # -----------------------------
    @classmethod
    def delete(cls, student_id):
        conn = cls.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
        conn.close()

    # -----------------------------
    # GET ALL STUDENTS
    # -----------------------------
    @classmethod
    def get_all(cls):
        conn = cls.connect()
        cur = conn.cursor()

        cur.execute("SELECT * FROM students ORDER BY student_id")
        rows = cur.fetchall()

        conn.close()

        students = []
        for row in rows:
            transcript_list = row["transcript"].split(",") if row["transcript"] else []
            students.append(
                Student(
                    row["student_id"],
                    row["name"],
                    row["last_name"],
                    row["email"],
                    row["program"],
                    row["level"],
                    transcript_list
                )
            )

        return students


# Auto-create table like course.py
Student.create_table()