# validation.py
from student import Student
from course import Course

MAX_CREDITS_DEFAULT = 18  # fallback if needed

def current_credit_load(student: Student):
    """Sum credits of courses the student is currently registered in."""
    total = 0
    for code in student.registered_courses:
        c = Course.get(code)
        if c:
            total += c.credits
    return total

def validate_registration(student_id, course_code, max_credits=None):
    """
    Returns (ok: bool, message: str)
    """
    student = Student.get(student_id)
    if student is None:
        return False, "Student not found."

    course = Course.get(course_code)
    if course is None:
        return False, "Course not found."

    # 1) Already registered?
    if course_code in student.registered_courses:
        return False, "Student already registered in this course."

    # 2) Capacity
    if course.is_full():
        return False, "Course is full."

    # 3) Prerequisites
    missing = [p for p in course.prerequisites if p not in student.transcript]
    if missing:
        return False, f"Missing prerequisites: {', '.join(missing)}"

    # 4) Level check (if course code encodes a level, optional)
    # If course has a 'level' encoded in its code (e.g., CS201 => level 2), you can parse; here we skip.

    # 5) Schedule conflict: compare schedule string with all registered courses
    for reg_code in student.registered_courses:
        reg_course = Course.get(reg_code)
        if reg_course and reg_course.schedule == course.schedule:
            return False, f"Schedule conflict with {reg_course.code}."

    # 6) Credit limit
    max_c = max_credits or getattr(student, "max_credits", MAX_CREDITS_DEFAULT)
    current = current_credit_load(student)
    if current + course.credits > max_c:
        return False, f"Credit limit exceeded ({current} + {course.credits} > {max_c})."

    return True, "OK"
