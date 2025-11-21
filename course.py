# Course.py
import sqlite3
from student import Student
class Course:
    def __init__(self,code,name,credits,lecture_hours,lab_hours,max_capacity, schedule, program, prerequisites=None, enrolled_students = 0):
        self.code = code
        self.name = name
        self.credits = credits
        self.lecture_hours = lecture_hours
        self.lab_hours = lab_hours
        self.max_capacity = max_capacity
        self.schedule = schedule
        self.program = program
        self.prerequisites = prerequisites or []
        self.enrolled_students = enrolled_students
    def isFull(self):
        #check if the course has the max enrolled students if true return true if false return false
        return self.enrolled_students >= self.max_capacity
    def CheckPrerequisites(self, student_transcript):
        # """Return True if all prerequisites are met.""" 
        return all(p in student_transcript for p in self.prerequisites)
    #--------------------
    # Database operations
    #--------------------
    @staticmethod
    def connect():
        conn = sqlite3.connect("courses.db")
        conn.row_factory = sqlite3.Row
        return conn
    @classmethod
    def create_table(cls):
        """Create the course tables if it doesn't exist"""
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses(
                       code TEXT PRIMARY KEY,
                       name TEXT,
                       credits INTEGER,
                       lecture_hours INTEGER,
                       lab_hours INTEGER,
                       max_capacity INTEGER,
                       schedule TEXT,
                       program TEXT,
                       prerequisites TEXT,
                       enrolled_students INTEGER
                       )""")
        conn.commit()
        conn.close()
    def save(self):
        """Insert or update this course in the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO courses
            (code, name, credits, lecture_hours, lab_hours, max_capacity, 
             schedule, program, prerequisites, enrolled_students)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.code, self.name, self.credits, self.lecture_hours,
            self.lab_hours, self.max_capacity, self.schedule, self.program,
            ",".join(self.prerequisites), self.enrolled_students
        ))
        conn.commit()
        conn.close()
    @classmethod
    def get(cls, code):
        """Retrieve a course by its code."""
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE code=?", (code,))
        row = cursor.fetchone()
        conn.close()
        if row:
            prereqs = [p.strip() for p in row["prerequisites"].split(",") if p.strip()]
            return cls(row["code"], row["name"], row["credits"],
                       row["lecture_hours"], row["lab_hours"],
                       row["max_capacity"], row["schedule"], row["program"], prereqs, row["enrolled_students"]
                       )
        return None

    @classmethod
    def all(cls):
        """Return a list of all courses."""
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses ORDER BY code")
        rows = cursor.fetchall()
        conn.close()
        courses = []
        for row in rows:
            prereqs = [p.strip() for p in row["prerequisites"].split(",") if p.strip()]
            courses.append(cls(row["code"], row["name"], row["credits"],
                               row["lecture_hours"], row["lab_hours"],
                               row["max_capacity"], row["schedule"], row["program"], prereqs, row["enrolled_students"]
                               ))
        return courses
    @classmethod
    def delete(cls, code):
        """Delete a course by its code."""
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE code=?", (code,))
        conn.commit()
        conn.close()
    def add_student(self):
        self.enrolled_students += 1

    def remove_student(self):
        self.enrolled_students -= 1
Course.create_table()
if __name__ == "__main__":
    import os
    import pandas as pd

    # Load CSV from same directory as course.py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "electrical_computer_program_courses.csv")

    print("Importing courses from:", csv_path)

    df = pd.read_csv(csv_path)

    Course.create_table()

    for _, row in df.iterrows():

        prereq_list = []
        if isinstance(row["Prerequisites"], str) and row["Prerequisites"].strip() != "":
            prereq_list = [p.strip() for p in row["Prerequisites"].split(",")]

        c = Course(
            code=row["Code"],
            name=row["Course Name"],
            credits=int(row["Credits"]),
            lecture_hours=0,
            lab_hours=0,
            max_capacity=40,
            schedule="TBA",
            program=row["Program"],
            prerequisites=prereq_list,
            enrolled_students=0
        )

        c.save()

    print("Courses imported successfully!")
