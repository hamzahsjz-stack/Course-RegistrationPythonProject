# registration.py
from student import Student
from course import Course
from validation import validate_registration

def register_student_to_course(student_id, course_code):
    student = Student.get(student_id)
    course = Course.get(course_code)

    if not student or not course:
        return False, "Student or course not found."

    # Check if already registered
    if course_code in student.registered_courses:
        return False, "Already registered in this course."

    if getattr(course,"schedule","") == "TBA":
        return False, "Cannot register due to there not being a schedule yet"
    # Check max capacity
    if course.isFull():
        return False, "Course is full."

    # Register student
    student.add_registered_course(course_code)
    student.save()
    course.add_student()
    course.save()
    
    return True, f"Successfully registered for {course.code} - {course.name}"

def unregister_student_from_course(student_id, course_code):
    student = Student.get(student_id)
    course = Course.get(course_code)

    if not student:
        return False, "Student not found."
    if not course:
        return False, "Course not found."

    if course_code not in student.registered_courses:
        return False, "Student is not registered in that course."
    
    # Remove from both records
    student.remove_registered_course(course_code)
    course.remove_student()
    student.save()
    course.save()

    return True, f"{student.name} unregistered from {course.code}."
