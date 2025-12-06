# app.py
import sys
from PyQt5 import QtWidgets, QtCore, QtGui
import os
from student import Student
from course import Course , bulk_import
from auth import Auth
from registration import register_student_to_course, unregister_student_from_course
# Helper utilities (app-local)
def normalizeCode(code):
    if not code:
        return ""
    return code.replace("-","").replace(" ","").upper()
def student_has_prereqs(student, course):
    """Return True if student has all prerequisites for course."""
    if not course.prerequisites:
        return True
    transcript = getattr(student, "transcript", [])  # list of course codes
    normalized_transcript = [normalizeCode(c) for c in transcript]  # normalize each code

    for p in course.prerequisites:
        if normalizeCode(p) not in normalized_transcript:
            return False
    return True

def schedules_conflict(s1, s2):
    """
    Return True if any day/time overlaps between two schedules.
    """
    s1_parsed = parse_schedule(s1)
    s2_parsed = parse_schedule(s2)

    for d1, start1, end1 in s1_parsed:
        for d2, start2, end2 in s2_parsed:
            if d1 == d2 and (start1 < end2 and start2 < end1):
                return True
    return False
def student_has_time_conflict(student, course):
    """
    Check if `course` conflicts with any course the student is registered in.
    Returns (bool_conflict, conflicting_course_code)
    """
    reg_codes = getattr(student, "registered_courses", []) or []
    for code in reg_codes:
        c = Course.get(code)
        if c and schedules_conflict(c.schedule, course.schedule):
            return True, c.code
    return False, None
# --------------------------
# Signup Dialog
# --------------------------
class SignupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Student Account")
        self.setGeometry(700, 350, 360, 420)
        layout = QtWidgets.QFormLayout(self)
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)
        self.username = QtWidgets.QLineEdit()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.first = QtWidgets.QLineEdit()
        self.last = QtWidgets.QLineEdit()
        self.email = QtWidgets.QLineEdit()
        self.program = QtWidgets.QLineEdit()       
        self.level = QtWidgets.QSpinBox()
        self.level.setRange(1, 10)
        self.level.setValue(1)

        layout.addRow("Username:", self.username)
        layout.addRow("Password:", self.password)
        layout.addRow("First Name:", self.first)
        layout.addRow("Last Name:", self.last)
        layout.addRow("Email:", self.email)
        layout.addRow("Program:", self.program)
        layout.addRow("Level:", self.level)

        self.btn_create = QtWidgets.QPushButton("Create Account")
        self.btn_create.clicked.connect(self.create_account)
        layout.addWidget(self.btn_create)

        self.message_label = QtWidgets.QLabel("")
        layout.addWidget(self.message_label)
    def create_account(self):
        uname = self.username.text().strip()
        pw = self.password.text().strip()
        first = self.first.text().strip()
        last = self.last.text().strip()
        email = self.email.text().strip()
        program = self.program.text().strip()
        level = int(self.level.value())   


        if not uname or not pw or not first or not last:
            self.message_label.setText("Please fill username, password, first and last name.")
            return
        
        if  (program.lower() == "computer") or  (program.lower() == "power") or  (program.lower() == "electronics") or (program.lower() == "biomedical"):
            pass
        else:
            QtWidgets.QMessageBox.warning(self,"failed", "Please enter a valid program : computer, power, biomedical, electronics")
            return

        # Check if create_student_account function is callable
        create_fn = getattr(Auth, "create_student_account", None)
        if callable(create_fn):
            # add the input into the create_student_account function which updates and saves the information into two databases
            ok, msg = Auth.create_student_account(uname, pw, first, last, email, program, level)
        self.message_label.setText(msg)
        if ok:
            student = Student.get(uname)        
        if student:
            # add courses to transcript depending on the level of the student
            lower_courses =[c.code for c in Course.all()
                            if getattr(c, "level", 0) < student.level
                            and (student.program in getattr(c,"program", ""))]
            student.transcript = list((getattr(student, "transcript", []) + lower_courses))
            student.save()
        if ok:
            QtWidgets.QMessageBox.information(self, "Success", msg)
            self.accept()

# --------------------------
# Login Window
# --------------------------
class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(600, 300, 320, 160)
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(self.password_input)

        hl = QtWidgets.QHBoxLayout()
        self.login_btn = QtWidgets.QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        hl.addWidget(self.login_btn)

        self.signup_btn = QtWidgets.QPushButton("Sign Up")
        self.signup_btn.clicked.connect(self.signup)
        hl.addWidget(self.signup_btn)

        layout.addLayout(hl)

        self.message_label = QtWidgets.QLabel("")
        layout.addWidget(self.message_label)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.message_label.setText("Enter username and password.")
            return

        user = Auth.authenticate(username, password)
        if user:
            # Ensure student profile exists for student role
            if user.get("role") == "student":
                sid = user.get("username")
                st = Student.get(sid)
                if st is None:
                    QtWidgets.QMessageBox.warning(self, "Error", 
                        "Student profile missing. Please recreate the account properly.")
                    return
            self.message_label.setText("Login successful!")
            self.main_window = MainMenuWindow(user)
            self.main_window.show()
            self.close()
        else:
            self.message_label.setText("Invalid username or password.")

    def signup(self):
        dialog = SignupDialog(self)
        dialog.exec_()
# Add Course Dialog (Admin)
class AddCourseDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Course")
        self.setGeometry(600, 300, 420, 320)
        layout = QtWidgets.QFormLayout(self)
        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)
        self.code = QtWidgets.QLineEdit() 
        self.name = QtWidgets.QLineEdit()
        self.credits = QtWidgets.QSpinBox()
        self.credits.setRange(1, 10)
        self.lecture = QtWidgets.QSpinBox()
        self.lecture.setRange(0, 10)
        self.lab = QtWidgets.QSpinBox()
        self.lab.setRange(0, 10)
        self.level = QtWidgets.QSpinBox()
        self.level.setRange(0, 10)
        self.max_capacity = QtWidgets.QSpinBox()
        self.max_capacity.setRange(1, 500)
        self.schedule = QtWidgets.QLineEdit()
        self.program = QtWidgets.QLineEdit()
        self.prereqs = QtWidgets.QLineEdit()

        self.schedule.setPlaceholderText("Mon-Wed-09:00-10:30")
        self.prereqs.setPlaceholderText("EE250,MATH110")

        layout.addRow("Course Code:", self.code)
        layout.addRow("Name:", self.name)
        layout.addRow("Credits:", self.credits)
        layout.addRow("Lecture hours:", self.lecture)
        layout.addRow("Lab hours:", self.lab)
        layout.addRow("level:", self.level)
        layout.addRow("Max Capacity:", self.max_capacity)
        layout.addRow("Schedule:", self.schedule)
        layout.addRow("Program:", self.program)
        layout.addRow("Prerequisites:", self.prereqs)

        add_btn = QtWidgets.QPushButton("Add Course")
        add_btn.clicked.connect(self.add_course)
        layout.addWidget(add_btn)

    def add_course(self):
        try:
            code = self.code.text().strip()
            name = self.name.text().strip()
            credits = int(self.credits.value())
            lecture = int(self.lecture.value())
            lab = int(self.lab.value())
            maxcap = int(self.max_capacity.value())
            level = int(self.level.value())
            schedule = self.schedule.text().strip()
            program = self.program.text().strip()

            # Convert comma-separated prereqs into string
            prereqs_list = [x.strip() for x in self.prereqs.text().split(",") if x.strip()]
            prereqs_str = ",".join(prereqs_list)

            if not code:
                QtWidgets.QMessageBox.warning(self, "Validation", "Course code required.")
                return

        except Exception as e:
            print(e)
            return

        try:
            c = Course(code, name, credits, lecture, lab, maxcap, schedule, program, level , prereqs_str, 0)
            c.save()
            QtWidgets.QMessageBox.information(self, "Success", f"Course {code} added.")
            self.accept()
        except Exception as e:
            print(e)
# edit Course Dialog (Admin)
class EditCourseDialog(QtWidgets.QDialog):
    def __init__(self, course_code, parent = None):   
            super().__init__(parent)
            self.setWindowTitle(f"Edit Course:{course_code}")
            self.setGeometry(600,300,420,320)
            self.course_code = course_code
            layout = QtWidgets.QFormLayout(self)
            font = QtGui.QFont("Segoe UI", 10)
            self.setFont(font)
            self.course = Course.get(course_code)

            if not self.course:
                QtWidgets.QMessageBox.warning(self, "Error", f"Course {course_code} not found.")
                self.reject()
                return
            
            self.code = QtWidgets.QLineEdit(self.course.code)
            self.code.setReadOnly(True) # NO changing read only
            self.name = QtWidgets.QLineEdit(getattr(self.course,"name", ""))
            self.credits = QtWidgets.QSpinBox()
            self.credits.setRange(1,10)
            self.credits.setValue(getattr(self.course,"credits",0))
            self.lecture = QtWidgets.QSpinBox()
            self.lecture.setRange(1,10)
            self.lecture.setValue(getattr(self.course,"lecture_hours", 0))
            self.lab = QtWidgets.QSpinBox()
            self.lab.setRange(0,10)
            self.lab.setValue(getattr(self.course,"lab_hours", 0))
            self.max_capacity = QtWidgets.QSpinBox()
            self.max_capacity.setRange(1,500)
            self.max_capacity.setValue(getattr(self.course,"max_capacity", 0))
            self.schedule = QtWidgets.QLineEdit(getattr(self.course,"schedule",""))
            self.program = QtWidgets.QLineEdit(getattr(self.course, "program", ""))
            self.level = QtWidgets.QSpinBox()
            self.level.setRange(1,10)
            self.level.setValue(getattr(self.course, "level", "0"))
            prereqs = getattr(self.course, "prerequisites", [])
            self.prereqs = QtWidgets.QLineEdit(",".join(prereqs))

            layout.addRow("Course Code:",self.code)
            layout.addRow("Name:",self.name)
            layout.addRow("Credits:",self.credits)
            layout.addRow("Lecture  hours:",self.lecture)
            layout.addRow("Lab hours:",self.lab)
            layout.addRow("max_capacity:",self.max_capacity)
            layout.addRow("schedule:",self.schedule)
            layout.addRow("program:",self.program)
            layout.addRow("prerequisites:",self.prereqs)
            layout.addRow("level", self.level)
            btn_save = QtWidgets.QPushButton("Save Changes")
            btn_save.clicked.connect(self.save_changes)
            layout.addWidget(btn_save)
            
    def save_changes(self):
                try:
                    self.course.name = self.name.text().strip()
                    self.course.credits = int(self.credits.value())
                    self.course.lecture_hours = int(self.lecture.value())
                    self.course.lab_hours = int(self.lab.value())
                    self.course.max_capacity = int(self.max_capacity.value())
                    self.course.schedule = self.schedule.text().strip()
                    self.course.program = self.program.text().strip()
                    self.course.level = int(self.level.text().strip())
                    self.course.prerequisites = [
                        x.strip() for x in self.prereqs.text().split(",") if x.strip()
                    ]
                    self.course.save()
                    QtWidgets.QMessageBox.information(self, "Success", f"Course {self.course_code} Updated")
                    self.accept()
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Error", f"Failed to save changes: {e}")
# Main Menu Window (Hub)
class MainMenuWindow(QtWidgets.QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        role = user.get("role", "student")
        self.setWindowTitle(f"Course Registration - {user.get('username')} ({role})")
        self.setGeometry(160, 80, 1000, 650)
        font = QtGui.QFont("Segoe UI", 10)
        
        self.setFont(font)
        self.central = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central)
        self.setStyleSheet("""QPushButton {font-size: 14px;
                                                        padding: 6px 40px;
                                                        border-radius: 5px;
                                                        background-color: #2d89ef;}
                                          QPushButton:hover{background-color: #1e5fb4;}""")
        # Menu panel
        self.menu_panel = QtWidgets.QWidget()
        menu_layout = QtWidgets.QVBoxLayout(self.menu_panel)
        welcome_label = QtWidgets.QLabel(f"Welcome, {user.get('username')} ({role})")
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        welcome_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        menu_layout.addWidget(welcome_label)
        menu_layout.setContentsMargins(15,15,15,15)
        menu_layout.setSpacing(30)
        menu_layout.setAlignment(QtCore.Qt.AlignCenter)
        # Buttons
        self.student_info_page = QtWidgets.QWidget()
        self.student_info_page_layout = QtWidgets.QVBoxLayout()
        self.student_info_page.setLayout(self.student_info_page_layout)
        btn_student_info = QtWidgets.QPushButton("View Student Information")
        btn_student_info.clicked.connect(self.show_student_info)
        menu_layout.addWidget(btn_student_info)
        # page that shows all the courses
        self.all_courses_page = QtWidgets.QWidget()
        self.all_courses_page_layout = QtWidgets.QVBoxLayout()
        self.all_courses_page.setLayout(self.all_courses_page_layout)
        btn_all_courses = QtWidgets.QPushButton("View All Courses")
        btn_all_courses.clicked.connect(self.show_all_courses)
        menu_layout.addWidget(btn_all_courses)
        # page that shows course registration
        self.registration_page = QtWidgets.QWidget()
        self.registration_page_layout = QtWidgets.QVBoxLayout()
        self.registration_page.setLayout(self.registration_page_layout)
        btn_register_courses = QtWidgets.QPushButton("Register / Unregister Courses")
        btn_register_courses.clicked.connect(self.show_registration)
        menu_layout.addWidget(btn_register_courses)
        # check if role is admin, if role is admin show admin options button
        if role == "admin":
            btn_admin = QtWidgets.QPushButton("Admin Options")
            btn_admin.clicked.connect(self.show_admin_options)
            menu_layout.addWidget(btn_admin)
        btn_logout = QtWidgets.QPushButton("Logout")
        btn_logout.clicked.connect(self.logout)
        menu_layout.addWidget(btn_logout)
        self.central.addWidget(self.menu_panel)   
        # Persistent admin widgets
        self.btn_add_course = QtWidgets.QPushButton("Add Course")
        self.btn_add_course.clicked.connect(self.open_add_course)
        self.admin_edit_input = QtWidgets.QLineEdit()
        self.admin_edit_input.setPlaceholderText("Course Code to edit")
        self.btn_edit_course = QtWidgets.QPushButton("Edit Course")
        self.btn_edit_course.clicked.connect(self.admin_edit_course)
        self.admin_delete_input = QtWidgets.QLineEdit()
        self.admin_delete_input.setPlaceholderText("Student ID to delete")
        self.btn_delete = QtWidgets.QPushButton("Delete Student")
        self.btn_delete.clicked.connect(self.admin_delete_student)
        # Pages placeholders
        self.admin_page = QtWidgets.QWidget()
        for w in (self.student_info_page, self.all_courses_page, self.registration_page, self.admin_page):
            self.central.addWidget(w)
        # For registration table reference
        self.registration_table = None
    # --------------------------
    # Navigation pages
    # --------------------------
    def show_student_info(self):      
        layout = self.student_info_page_layout     
        # clear previous layout contents
        self._clear_layout(layout)
        layout.addWidget(QtWidgets.QLabel("Student Information"))
        list_widget = QtWidgets.QListWidget()
        if self.user.get("role") == "student":
            s = Student.get(self.user.get("username"))
            s1 = f"{s.student_id} | {s.name} {s.last_name} | Email: {s.email} | Program: {s.program} | Level: {s.level} | Registered: {','.join(getattr(s,'registered_courses',[]) or []) } | Transcript: {(getattr(s,'transcript',[]) or [])}"
            if s:
                list_widget.addItem(s1)
            else:
                list_widget.addItem("Student profile not found.")
        else:
            for s in Student.get_all():
                list_widget.addItem(f"{s.student_id} | {s.name} {s.last_name} | Email: {s.email} | Program: {s.program} | Level: {s.level} | Registered: {','.join(getattr(s,'registered_courses',[]) or [])}")
        layout.addWidget(list_widget)
        Complete_course_btn = QtWidgets.QPushButton("Complete registered Courses")
        Complete_course_btn.clicked.connect(self.add_course_to_transcript)
        back_btn = QtWidgets.QPushButton("Back to Menu")
        back_btn.clicked.connect(lambda: self.central.setCurrentWidget(self.menu_panel))
        if self.user.get("role") == "student":
            layout.addWidget(Complete_course_btn)
        layout.addWidget(back_btn)
        self.central.setCurrentWidget(self.student_info_page)

    def show_all_courses(self):
        layout = self.all_courses_page_layout
        self._clear_layout(layout)
        layout.addWidget(QtWidgets.QLabel("All Courses"))
        list_widget = QtWidgets.QListWidget()
        for c in Course.all():
            list_widget.addItem(f"{c.code} | {c.name} | Credits: {c.credits} | Enrolled: {c.enrolled_students}/{c.max_capacity} | Schedule: {getattr(c,'schedule','')} | Program:{getattr(c,'program','')} | Prereqs: {','.join(getattr(c,'prerequisites',[]) or [])}")
        layout.addWidget(list_widget)
        back_btn = QtWidgets.QPushButton("Back to Menu")
        back_btn.clicked.connect(lambda: self.central.setCurrentWidget(self.menu_panel))
        layout.addWidget(back_btn)
        self.central.setCurrentWidget(self.all_courses_page)

    def show_registration(self):
        layout = self.registration_page_layout
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.registration_page)
        else:
            self._clear_layout(layout)
        layout.addWidget(QtWidgets.QLabel("Register / Unregister Courses"))
        # Info label for student
        if self.user.get("role") == "student":
            sid = self.user.get("username")
            student = Student.get(sid)            
            info = QtWidgets.QLabel(f"Student: {student.student_id} — {student.name} {student.last_name} | Program: {student.program} | Level: {student.level}")
            layout.addWidget(info)
        else:
            # admin view: ask which student to act as (optional)
            info = QtWidgets.QLabel("Admin: select a student ID when registering via the Register button.")
            layout.addWidget(info)
            student = None
        # Table
        sid = self.user.get("username")
        student = Student.get(sid)
        table = QtWidgets.QTableWidget()
        self.registration_table = table
        courses = Course.all()
        valid_courses = []
        for c in courses:
            if student:
                if ( student.program not in getattr(c,"program","")):
                    continue
                # Only same level
                if (getattr(c, "code", "") in student.transcript):
                    continue
            valid_courses.append(c)
        table.setRowCount(len(valid_courses))
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels(["Code", "Name", "Prereqs", "Schedule", "program" , "Credits", "Max", "Enrolled", "Level", "status"])
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        for i, c in enumerate(valid_courses):
            
            prereq_text = ",".join(getattr(c, "prerequisites", []) or [])
            maxcap = getattr(c, "max_capacity", "")
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(c.code)))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(getattr(c, "name", ""))))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(prereq_text))
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(getattr(c, "schedule", ""))))
            table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(getattr(c, "program", ""))) )
            table.setItem(i, 5, QtWidgets.QTableWidgetItem(str(getattr(c, "credits", ""))))
            table.setItem(i, 6, QtWidgets.QTableWidgetItem(str(maxcap)))
            table.setItem(i, 7, QtWidgets.QTableWidgetItem(str(getattr(c,"enrolled_students", ""))))
            table.setItem(i, 8, QtWidgets.QTableWidgetItem(str(getattr(c,"level",""))))
            # Determine status
            status = "Available"
            if self.user.get("role") == "student":
                # check registered (using registered_courses)
                registered_list = getattr(student, "registered_courses", None)
                if c.code in registered_list:
                    status = "Registered"
                elif not student_has_prereqs(student, c):
                    status = "Missing prereqs"
                else:
                    conflict, conflict_code = student_has_time_conflict(student, c)
                    if conflict:
                        status = f"Time conflict with {conflict_code}"
            else:
                status = "N/A (admin)"

            table.setItem(i, 9, QtWidgets.QTableWidgetItem(status))
           
        table.resizeColumnsToContents()
        layout.addWidget(table)
        # Buttons under the table
        btn_hbox = QtWidgets.QHBoxLayout()
        btn_reg = QtWidgets.QPushButton("Register Selected")
        btn_unreg = QtWidgets.QPushButton("Unregister Selected")
        btn_timetable = QtWidgets.QPushButton("Show Timetable for Registered")
        btn_refresh = QtWidgets.QPushButton("Refresh")
        btn_hbox.addWidget(btn_reg)
        btn_hbox.addWidget(btn_unreg)
        if self.user.get("role") == "student": # only student can see his timetable 
            btn_hbox.addWidget(btn_timetable)
        btn_hbox.addWidget(btn_refresh)
        btn_hbox.setSpacing(10)
        layout.addLayout(btn_hbox)
        # Connect buttons
        btn_reg.clicked.connect(self.handle_register_from_table)
        btn_unreg.clicked.connect(self.handle_unregister_from_table)
        btn_timetable.clicked.connect(self.show_full_timetable)
        btn_refresh.clicked.connect(self.show_registration)
        # Back
        back_btn = QtWidgets.QPushButton("Back to Menu")
        back_btn.clicked.connect(lambda: self.central.setCurrentWidget(self.menu_panel))
        layout.addWidget(back_btn)
        self.central.setCurrentWidget(self.registration_page)
    # --------------------------
    # Admin page
    # --------------------------
    def show_admin_options(self):
        layout = QtWidgets.QVBoxLayout(self.admin_page)
        self._clear_layout(layout)
        layout.addWidget(QtWidgets.QLabel("Admin Options"))
        # Add Course button
        layout.addWidget(self.btn_add_course)
        # Edit Course by code
        hl_edit = QtWidgets.QHBoxLayout()
        hl_edit.addWidget(self.admin_edit_input)
        hl_edit.addWidget(self.btn_edit_course)
        layout.addLayout(hl_edit)
        # Delete student by student_id
        hl = QtWidgets.QHBoxLayout()        
        hl.addWidget(self.admin_delete_input)
        hl.addWidget(self.btn_delete)
        layout.addLayout(hl)
        # Back
        back_btn = QtWidgets.QPushButton("Back to Menu")
        back_btn.clicked.connect(lambda: self.central.setCurrentWidget(self.menu_panel))
        layout.addWidget(back_btn)
        self.central.setCurrentWidget(self.admin_page)
    def admin_edit_course(self):
        self.admin_edit_input.clearFocus()
        code = self.admin_edit_input.text().strip()
        if not code:
            QtWidgets.QMessageBox.warning(self, "Input", "Enter a course code to edit.")
            return
        self.open_edit_course(code)
    def admin_delete_student(self):
        sid = self.admin_delete_input.text().strip()
        if not sid:
            QtWidgets.QMessageBox.warning(self, "Input", "Enter student id to delete.")
            return
        # delete auth user if any
        try:
            Auth.delete_user(sid)
        except Exception as e:
            print(e)
        sid_exists = Student.get(sid)
        if sid_exists != None:
            Student.delete(sid)
            QtWidgets.QMessageBox.information(self, "Deleted", f"Student {sid} deleted (best-effort).")
            # frontend refresh 
            self.show_student_info()
        else:
            QtWidgets.QMessageBox.information(self, "Student with", f"{sid} doesn't exist")
        # delete student record
        
    # --------------------------
    # Handlers for table actions
    # --------------------------
    def handle_register_from_table(self):
        row = self.registration_table.currentRow()  
        # check if row is selected      
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Select", "Select a course row first.")
            return
        # set the code that is returned to the row that is selected and coloumn 0
        code = self.registration_table.item(row, 0).text()
        if self.user.get("role") == "student":
            sid = self.user.get("username")        
        else:
            sid, ok = QtWidgets.QInputDialog.getText(self, "Student ID", "Enter student ID to register:")
            if not ok or not sid:
                return
        # get student and course object
        student = Student.get(sid)
        course = Course.get(code)
        # check if student has time conflict in his registered courses with the course schedule
        check, code = student_has_time_conflict(student,course)
        if check:
            QtWidgets.QMessageBox.warning(self, "Failed", f"Cannot register to {code} due to time conflict")
            return
        ok, msg = register_student_to_course(sid, course.code)

        if ok and not check:
            QtWidgets.QMessageBox.information(self, "Registered", msg)
        
        elif getattr(course, "schedule", "") == "TBA":
            QtWidgets.QMessageBox.warning(self, "Failed", f"Cannot register due there not being a schedule yet")
            return
        elif not student_has_prereqs(student,course):
            QtWidgets.QMessageBox.warning(self,"failed", f"Cannot register due to missing prereqs")
        else:
            QtWidgets.QMessageBox.warning(self, "Failed", msg)
        # refresh
        self.show_registration()

    def handle_unregister_from_table(self):
        row = self.registration_table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Select", "Select a course row first.")
            return
        code = self.registration_table.item(row, 0).text()
        if self.user.get("role") == "student":
            sid = self.user.get("username")
                #refresh student information page                
        else:
            sid, ok = QtWidgets.QInputDialog.getText(self, "Student ID", "Enter student ID to unregister:")
            if not ok or not sid:
                return
        ok, msg = unregister_student_from_course(sid, code)
        if ok:
            QtWidgets.QMessageBox.information(self, "Unregistered", msg)         
        else:
            QtWidgets.QMessageBox.warning(self, "Failed", msg)
        self.show_registration()  
    # open timetable function  
    def show_full_timetable(self):
        sid = self.user.get("username")
        student = Student.get(sid)
        reg = getattr(student, "registered_courses", [])
        courses = [Course.get(c) for c in reg if Course.get(c)]
        dlg = TimetableWindow(courses, self)
        dlg.exec_()
    # adding registered courses to transcript
    def add_course_to_transcript(self):
        sid = self.user.get("username")
        student = Student.get(sid)
        total_credits = 0
        reg_courses = student.registered_courses
        if reg_courses == None or []:
            QtWidgets.QMessageBox.warning(self,"failed", "No registered courses yet")
            return
        else:
            for c in reg_courses:
                c1 = Course.get(c)
                total_credits += int(getattr(c1,"credits",""))
                print(total_credits)
            if int(total_credits) > 18:
                QtWidgets.QMessageBox.warning(self,"failed", "Cannot complete courses due to high credits please remove a course")
                return
            elif int(total_credits) < 12:
                QtWidgets.QMessageBox.warning(self,"failed","Cannot complete courses due to low credits please add a course")
                return
            else:
                student.transcript = list((getattr(student, "transcript", []) + reg_courses))
                student.save()
                QtWidgets.QMessageBox.information(self,"Success", "Successfully completed courses and added to transcript")
    def open_edit_course(self, code):
        dlg = EditCourseDialog(code, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.show_all_courses()
    def open_add_course(self):
        dlg = AddCourseDialog(self)
        dlg.exec_()
        # refresh pages that show courses
        self.show_all_courses()
    def logout(self):
        self.login = LoginWindow()
        self.login.show()
        self.close()
    # remove widgets from layout 
    def _clear_layout(self, layout):
        """Remove all widgets from a layout."""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                # nested layouts
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)
# Schedule parser + Timetable UI
DAY_TO_IDX = {"sun":0, "mon":1, "tue":2, "wed":3, "thu":4, "fri":5, "sat":6}
IDX_TO_DAY = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
# parsing or transforming string schedule to indexes and minutes
def parse_schedule(schedule):
    """
    Flexible parser for schedules like:
    - Sun-09:00-10:30
    - Sun-Tue-Thu-09:00-10:30
    - Mon-Wed-13:00-15:00   (NOT a range → just Mon and Wed)
    """
    if not schedule:
        return []
    # if schedule = Sun-Tue-Thu-9:00-9:50 then parts = ["Sun", "Tue", "Thu", "9:00", "9:50"]
    parts = schedule.split("-")
   
    # last two must be times
    if len(parts) < 3:
        return []
    start_time = parts[-2]
    end_time   = parts[-1]
    day_parts  = parts[:-2]      # all before times
    def to_minutes(t):
        h, m = map(int, t.split(":"))
        return h * 60 + m
    start_min = to_minutes(start_time)
    end_min   = to_minutes(end_time)

    results = []

    # treat EACH item as one day (no ranges!)
    for d in day_parts:
        key = d.lower()
        if key in DAY_TO_IDX:
            results.append((DAY_TO_IDX[key], start_min, end_min))
    return results
# Timetable gui class 
class TimetableWindow(QtWidgets.QDialog):
    def __init__(self, courses, parent=None):
        super().__init__(parent)
        self.courses = courses
        self.setWindowTitle("Timetable")
        self.resize(900, 600)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Weekly Timetable")
        title.setStyleSheet("font-size:18px; font-weight:bold; color:black;")
        layout.addWidget(title)

        self.view = QtWidgets.QGraphicsView()
        self.scene = QtWidgets.QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setBackgroundBrush(QtGui.QColor(30,30,30))
        layout.addWidget(self.view)
        btn = QtWidgets.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

        self.draw()
    def color_for(self, name):
        h = abs(hash(name)) % 360
        c = QtGui.QColor()
        c.setHsl(h, 180, 140)
        return c
    def draw(self):
        scene = self.scene
        days = ["Sun","Mon","Tue","Wed","Thu"]
        left = 60
        top = 30
        width = 800
        height = 500
        col_w = width / len(days)
        hour_h = height / (23 - 8)  # from 8:00 to 23:00

        # day headers
        for i, d in enumerate(days):
            x = left + i*col_w
            scene.addText(d).setPos(x+10, 5)

        # horizontal lines (hours)
        for hour in range(8, 24):
            y = top + (hour-8) * hour_h
            scene.addLine(left, y, left+width, y, QtGui.QPen(QtGui.QColor(80,80,80)))
            label = scene.addText(f"{hour}:00")
            label.setPos(5, y-8)

        # draw blocks
        for c in self.courses:
            blocks = parse_schedule(c.schedule)
            for (day_i, start_min, end_min) in blocks:
                if day_i > 4: 
                    continue   # only Sunday to Thursday Not Friday and saturday
                start_hour = start_min / 60
                end_hour = end_min / 60
                x = left + day_i * col_w + 5
                y = top + (start_hour - 8) * hour_h
                h = (end_hour - start_hour) * hour_h
                rect = QtCore.QRectF(x, y, col_w - 10, h - 5)

                # rounded box
                path = QtGui.QPainterPath()
                path.addRoundedRect(rect, 6, 6)
                color = self.color_for(c.code)
                scene.addPath(path, QtGui.QPen(QtCore.Qt.white), QtGui.QBrush(color))

                # text inside
                text = f"{c.code}\n{c.name}\n{c.schedule}"
                t = scene.addText(text)
                t.setDefaultTextColor(QtCore.Qt.white)
                t.setTextWidth(rect.width()-4)
                t.setPos(rect.left()+4, rect.top()+4)
# --------------------------
# Main: ensure default admin and start app
# --------------------------
if __name__ == "__main__":
    # ensure default admin exists
    if Auth.get_user("admin") is None:
        try:
            pw = Auth.hash_password("admin123")
        except Exception:
            pw = "admin123"
        Auth.add_user("admin", pw, role="admin", student_id=None)
        print("Default admin created: username='admin', password='admin123'")
    Course.create_table()  # ensure table exists
    # Connect to DB
    import sqlite3
    conn = sqlite3.connect("courses.db")
    cur = conn.cursor()

    # Check if table is empty
    cur.execute("SELECT COUNT(*) FROM courses")
    count = cur.fetchone()[0]
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "electrical_program_courses.csv")
    # Import only once
    if count == 0:       
        bulk_import(csv_path)
        print("Bulk import done (first time).")
    else:
        print("Courses already loaded.")

    conn.close()
    app = QtWidgets.QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())
    login.show()
    sys.exit(app.exec_())
