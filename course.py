# Course.py
import sqlite3
import pandas as pd
import os

class Course:
    def __init__(
        self, code, name, credits, lecture_hours=0, lab_hours=0, max_capacity=0,
        schedule="", program="", level=None, prerequisites=None, enrolled_students=0
    ):
        self.code = code
        self.name = name
        self.credits = credits
        self.lecture_hours = lecture_hours
        self.lab_hours = lab_hours
        self.max_capacity = max_capacity
        self.schedule = schedule
        self.program = program               # <--- ONLY 1 PROGRAM
        self.level = level
        self.prerequisites = prerequisites or []
        self.enrolled_students = enrolled_students

    # --------------------
    # Database operations
    # --------------------
    @staticmethod
    def connect():
        conn = sqlite3.connect("courses.db")
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def create_table(cls):
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
                program TEXT,                  -- <--- SINGLE PROGRAM
                level INTEGER,
                prerequisites TEXT,
                enrolled_students INTEGER
            )
        """)
        conn.commit()
        conn.close()

    def save(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO courses
            (code, name, credits, lecture_hours, lab_hours, max_capacity,
             schedule, program, level, prerequisites, enrolled_students)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.code, self.name, self.credits, self.lecture_hours,
            self.lab_hours, self.max_capacity, self.schedule,
            self.program, self.level,
            ", ".join(self.prerequisites), self.enrolled_students
        ))

        conn.commit()
        conn.close()

    @classmethod
    def get(cls, code):
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE code=?", (code,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        prereqs = [p.strip() for p in row["prerequisites"].split(",") if p.strip()]

        return cls(
            code=row["code"],
            name=row["name"],
            credits=row["credits"],
            lecture_hours=row["lecture_hours"],
            lab_hours=row["lab_hours"],
            max_capacity=row["max_capacity"],
            schedule=row["schedule"],
            program=row["program"],       # <--- SINGLE PROGRAM
            level=row["level"],
            prerequisites=prereqs,
            enrolled_students=row["enrolled_students"]
        )
    def isFull(self):
        #check if the course has the max enrolled students if true return true if false return false
        return self.enrolled_students >= self.max_capacity
    @classmethod
    def all(cls):
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses ORDER BY code")
        rows = cursor.fetchall()
        conn.close()

        courses = []
        for row in rows:
            prereqs = [p.strip() for p in row["prerequisites"].split(",") if p.strip()]
            courses.append(cls(
                code=row["code"],
                name=row["name"],
                credits=row["credits"],
                lecture_hours=row["lecture_hours"],
                lab_hours=row["lab_hours"],
                max_capacity=row["max_capacity"],
                schedule=row["schedule"],
                program=row["program"],       # <--- SINGLE PROGRAM
                level=row["level"],
                prerequisites=prereqs,
                enrolled_students=row["enrolled_students"]
            ))
        return courses

    @classmethod
    def delete(cls, code):
        conn = cls.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE code=?", (code,))
        conn.commit()
        conn.close()

    def add_student(self):
        self.enrolled_students += 1

    def remove_student(self):
        self.enrolled_students -= 1


# --------------------
# CSV Bulk Import Tool
# --------------------
if __name__ == "__main__":
    Course.create_table()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "electrical_program_courses.csv")

    def bulk_import(csv_file):
        df = pd.read_csv(csv_file)
        df.columns = df.columns.str.strip()

        merged = {}

        for _, row in df.iterrows():
            code = str(row["Code"]).strip()
            name = str(row["Course Name"]).strip()
            credits_raw = str(row["Credits"]).strip()

            try:
                credits = int(credits_raw)
            except ValueError:
                print(f"[WARNING] Invalid credits value '{credits_raw}' in course {code}. Setting credits to 0.")
                credits = 0

            level = row.get("Level", None)

            # clean prerequisites
            prereq_list = []
            if "Prerequisites" in df.columns and not pd.isna(row["Prerequisites"]):
                prereq_list = [
                    p.strip() for p in str(row["Prerequisites"]).split(",") if p.strip()
                ]

            program = str(row.get("Program", "")).strip()

            if code not in merged:
                # create new entry
                merged[code] = {
                    "name": name,
                    "credits": credits,
                    "level": level,
                    "prereqs": set(prereq_list),
                    "programs": set([program]) if program else set(),
                }
            else:
                # merge prereqs + programs
                merged[code]["prereqs"].update(prereq_list)
                if program:
                    merged[code]["programs"].add(program)

        # Insert into the database
        for code, data in merged.items():
            course = Course(
                code=code,
                name=data["name"],
                credits=data["credits"],
                lecture_hours=0,
                lab_hours=0,
                max_capacity=20,
                schedule="TBA",
                program=", ".join(sorted(data["programs"])),
                level=data["level"],
                prerequisites=sorted(list(data["prereqs"]))
            )
            course.save()

        print(f"Merged import complete. {len(merged)} unique courses imported.")

    bulk_import(csv_path)
