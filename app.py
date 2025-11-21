# app.py
import sys
from PyQt5 import QtWidgets, QtCore
from student import Student
from course import Course
from auth import Auth
from registration import register_student_to_course, unregister_student_from_course

# --------------------------
# Helper utilities (app-local)
# --------------------------
def safe_enrolled_count(course):
    """Return number of enrolled students - support int or list storage."""
    val = getattr(course, "enrolled_students", None)
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    try:
        return len(val)
    except Exception:
        return 0

def student_has_prereqs(student, course):
    """Return True if student has all prerequisites for course."""
    if not course.prerequisites:
        return True
    transcript = getattr(student, "transcript", []) or []
    return all(p in transcript for p in course.prerequisites)

def schedules_conflict(s1, s2):
    """
    Lightweight schedule conflict detection.
    Currently compares normalized strings and common tokens.
    Examples supported: "Mon-09:00-10:30", "Mon-Wed-09:00-10:30", "Tue-14"
    This is intentionally simple — matches day tokens and time substrings.
    """
    if not s1 or not s2:
        return False
    a = s1.lower().replace(" ", "")
    b = s2.lower().replace(" ", "")
    # easy equality (exact)
    if a == b:
        return True
    # split by separators to find day tokens
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    # find day tokens in each
    def find_days(s):
        found = set()
        for d in days:
            if d in s:
                found.add(d)
        return found
    da = find_days(a)
    db = find_days(b)
    if not da or not db:
        # fallback: if any time substring overlaps (hh:mm)
        time_tokens = []
        for token in (a.split("-") + b.split("-")):
            if ":" in token or token.isdigit():
                time_tokens.append(token)
        # if any time token matches and at least one day overlap by substring:
        if any(t in a and t in b for t in time_tokens):
            return True
        return False
    if da.intersection(db):
        # if they share a day, check if time substrings likely overlap
        # crude: if any digits/time substring is shared
        tokens_a = [t for t in a.split("-") if any(ch.isdigit() for ch in t)]
        tokens_b = [t for t in b.split("-") if any(ch.isdigit() for ch in t)]
        if not tokens_a or not tokens_b:
            return True
        for ta in tokens_a:
            for tb in tokens_b:
                if ta == tb or ta in tb or tb in ta:
                    return True
        # otherwise assume conflict if same day (safe default)
        return True
    return False

def student_has_time_conflict(student, course):
    """Check if `course` conflicts with any course student is currently registered in."""
    reg_codes = getattr(student, "registered_courses", []) or getattr(student, "transcript", []) or []
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
        # Prefer Auth.create_student_account if available
        create_fn = getattr(Auth, "create_student_account", None)
        if callable(create_fn):
            ok, msg = Auth.create_student_account(uname, pw, first, last, email, program, level)
            print("works")
        self.message_label.setText(msg)
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



# --------------------------
# Add Course Dialog (Admin)
# --------------------------
class AddCourseDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Course")
        self.setGeometry(600, 300, 420, 320)
        layout = QtWidgets.QFormLayout(self)

        self.code = QtWidgets.QLineEdit()
        self.name = QtWidgets.QLineEdit()
        self.credits = QtWidgets.QSpinBox()
        self.credits.setRange(1, 10)
        self.lecture = QtWidgets.QSpinBox()
        self.lecture.setRange(0, 10)
        self.lab = QtWidgets.QSpinBox()
        self.lab.setRange(0, 10)
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
            schedule = self.schedule.text().strip()
            program = self.program.text().strip()
            prereqs = [x.strip() for x in self.prereqs.text().split(",") if x.strip()]

            if not code:
                QtWidgets.QMessageBox.warning(self, "Validation", "Course code required.")
                return
        except Exception as e:
            print(e)

        # Try to use Course.save-like API: prefer Course(...) and .save() if available
        try:
            # try constructor signature used earlier in your project
            c = Course(code, name, credits, lecture, lab, maxcap, schedule, program, prereqs, 0)
            c.save()
            QtWidgets.QMessageBox.information(self, "Success", f"Course {code} added.")
            self.accept()
        except Exception as e:
            print(e)
# --------------------------
# edit Course Dialog (Admin)
# --------------------------
class EditCourseDialog(QtWidgets.QDialog):
    def __init__(self, course_code, parent = None):
        
            super().__init__(parent)
            self.setWindowTitle(f"Edit Course:{course_code}")
            self.setGeometry(600,300,420,320)
            self.course_code = course_code
            layout = QtWidgets.QFormLayout(self)

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
            self.credits.setValue(getattr(self.course,"credits",""))
            self.lecture = QtWidgets.QSpinBox()
            self.lecture.setRange(1,10)
            self.lecture.setValue(getattr(self.course,"lecture_hours", ""))
            self.lab = QtWidgets.QSpinBox()
            self.lab.setRange(0,10)
            self.lab.setValue(getattr(self.course,"lab_hours", ""))
            self.max_capacity = QtWidgets.QSpinBox()
            self.max_capacity.setRange(1,500)
            self.max_capacity.setValue(getattr(self.course,"max_capacity", ""))
            self.schedule = QtWidgets.QLineEdit(getattr(self.course,"schedule",""))
            self.program = QtWidgets.QLineEdit(getattr(self.course, "program", ""))
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
                    self.course.prerequisites = [x.strip() for x in self.prereqs.text().strip(",") if x.strip()]
                    self.course.save()
                    QtWidgets.QMessageBox.information(self, "Success", f"Course {self.course_code} Updated")
                    self.accept()
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Error", f"Failed to save changes: {e}")
# --------------------------
# Main Menu Window (Hub)
# --------------------------
class MainMenuWindow(QtWidgets.QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        role = user.get("role", "student")
        self.setWindowTitle(f"Course Registration - {user.get('username')} ({role})")
        self.setGeometry(160, 80, 1000, 650)

        self.central = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central)

        # Menu panel
        self.menu_panel = QtWidgets.QWidget()
        menu_layout = QtWidgets.QVBoxLayout(self.menu_panel)
        welcome_label = QtWidgets.QLabel(f"Welcome, {user.get('username')} ({role})")
        welcome_label.setAlignment(QtCore.Qt.AlignCenter)
        welcome_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        menu_layout.addWidget(welcome_label)
        # Buttons
        btn_student_info = QtWidgets.QPushButton("View Student Information")
        btn_student_info.clicked.connect(self.show_student_info)
        menu_layout.addWidget(btn_student_info)

        btn_all_courses = QtWidgets.QPushButton("View All Courses")
        btn_all_courses.clicked.connect(self.show_all_courses)
        menu_layout.addWidget(btn_all_courses)

        btn_register_courses = QtWidgets.QPushButton("Register / Unregister Courses")
        btn_register_courses.clicked.connect(self.show_registration)
        menu_layout.addWidget(btn_register_courses)

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

        self.student_info_page = QtWidgets.QWidget()
        self.all_courses_page = QtWidgets.QWidget()
        self.program_courses_page = QtWidgets.QWidget()
        self.registration_page = QtWidgets.QWidget()
        self.admin_page = QtWidgets.QWidget()

        for w in (self.student_info_page, self.all_courses_page, self.program_courses_page, self.registration_page, self.admin_page):
            self.central.addWidget(w)

        # For registration table reference
        self.registration_table = None

    # --------------------------
    # Navigation pages
    # --------------------------
    def show_student_info(self):

        layout = self.student_info_page.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.student_info_page)
        # clear previous layout contents
        self._clear_layout(layout)
        layout.addWidget(QtWidgets.QLabel("Student Information"))
        list_widget = QtWidgets.QListWidget()
        if self.user.get("role") == "student":
            s = Student.get(self.user.get("username"))
            if s:
                list_widget.addItem(f"{s.student_id} | {s.name} {s.last_name} | Email: {s.email} | Program: {s.program} | Level: {s.level} | Registered: {','.join(getattr(s,'registered_courses',[]) or [])}")
            else:
                list_widget.addItem("Student profile not found.")
        else:
            for s in Student.get_all():
                list_widget.addItem(f"{s.student_id} | {s.name} {s.last_name} | Email: {s.email} | Program: {s.program} | Level: {s.level} | Registered: {','.join(getattr(s,'registered_courses',[]) or [])}")
        layout.addWidget(list_widget)

        back_btn = QtWidgets.QPushButton("Back to Menu")
        back_btn.clicked.connect(lambda: self.central.setCurrentWidget(self.menu_panel))
        layout.addWidget(back_btn)
        self.central.setCurrentWidget(self.student_info_page)

    def show_all_courses(self):
        layout = QtWidgets.QVBoxLayout(self.all_courses_page)
        self._clear_layout(layout)
        layout.addWidget(QtWidgets.QLabel("All Courses"))
        list_widget = QtWidgets.QListWidget()
        for c in Course.all():
            list_widget.addItem(f"{c.code} | {c.name} | Credits: {getattr(c,'credits', '')} | Enrolled: {safe_enrolled_count(c)}/{getattr(c,'max_capacity', getattr(c,'maxcap', ''))} | Schedule: {getattr(c,'schedule','')} | Program:{getattr(c,'program','')} | Prereqs: {','.join(getattr(c,'prerequisites',[]) or [])}")
        layout.addWidget(list_widget)

        back_btn = QtWidgets.QPushButton("Back to Menu")
        back_btn.clicked.connect(lambda: self.central.setCurrentWidget(self.menu_panel))
        layout.addWidget(back_btn)
        self.central.setCurrentWidget(self.all_courses_page)


    def show_registration(self):
        layout = QtWidgets.QVBoxLayout(self.registration_page)
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
        table = QtWidgets.QTableWidget()
        self.registration_table = table
        courses = Course.all()
        table.setRowCount(len(courses))
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels(["Code", "Name", "Prereqs", "Schedule", "program" , "Credits", "Max", "Enrolled", "Status"])
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        for i, c in enumerate(courses):
            prereq_text = ",".join(getattr(c, "prerequisites", []) or [])
            enrolled = safe_enrolled_count(c)
            maxcap = getattr(c, "max_capacity", getattr(c, "maxcap", getattr(c, "capacity", "")))
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(c.code)))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(getattr(c, "name", ""))))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(prereq_text))
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(getattr(c, "schedule", ""))))
            table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(getattr(c, "program", ""))) )
            table.setItem(i, 5, QtWidgets.QTableWidgetItem(str(getattr(c, "credits", ""))))
            table.setItem(i, 6, QtWidgets.QTableWidgetItem(str(maxcap)))
            table.setItem(i, 7, QtWidgets.QTableWidgetItem(str(enrolled)))

            # Determine status
            status = "Available"
            if student:
                # check registered (use registered_courses or transcript depending on your implementation)
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

            table.setItem(i, 7, QtWidgets.QTableWidgetItem(status))

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
        btn_hbox.addWidget(btn_timetable)
        btn_hbox.addWidget(btn_refresh)
        layout.addLayout(btn_hbox)

        # Connect buttons
        btn_reg.clicked.connect(self.handle_register_from_table)
        btn_unreg.clicked.connect(self.handle_unregister_from_table)
        btn_timetable.clicked.connect(self.handle_timetable_from_table)
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
        
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Select", "Select a course row first.")
            return
        code = self.registration_table.item(row, 0).text()
        
        if self.user.get("role") == "student":
            sid = self.user.get("username")
            
            #refresh student information page
            
        else:
            sid, ok = QtWidgets.QInputDialog.getText(self, "Student ID", "Enter student ID to register:")
            if not ok or not sid:
                return
      
        # call registration function
        ok, msg = register_student_to_course(sid, code)
        if ok:
            QtWidgets.QMessageBox.information(self, "Registered", msg)
        else:
            QtWidgets.QMessageBox.warning(self, "Failed", msg)
        # refresh
        self.show_student_info()
        self.show_registration()



    def handle_unregister_from_table(self):
        try:
            row = self.registration_table.currentRow()
            if row < 0:
                QtWidgets.QMessageBox.warning(self, "Select", "Select a course row first.")
                return
            code = self.registration_table.item(row, 0).text()
            if self.user.get("role") == "student":
                sid = self.user.get("username")
                #refresh student information page
                self.show_student_info()
                
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
        except Exception as e:
            print(e)

    def handle_timetable_from_table(self):
        row = self.registration_table.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Select", "Select a course row first.")
            return
        code = self.registration_table.item(row, 0).text()
        c = Course.get(code)
        if not c:
            QtWidgets.QMessageBox.warning(self, "Not found", "Course not found.")
            return
        self.show_course_timetable(c)

    # --------------------------
    # small helpers
    # --------------------------
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

    def _clear_layout(self, layout):
        """Remove all widgets from a layout (helper)."""
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


# --------------------------
# Main: ensure default admin and start app
# --------------------------
if __name__ == "__main__":
    # ensure default admin exists
    try:
        if Auth.get_user("admin") is None:
            try:
                pw = Auth.hash_password("admin123")
            except Exception:
                pw = "admin123"
            Auth.add_user("admin", pw, role="admin", student_id=None)
            print("Default admin created: username='admin', password='admin123'")
    except Exception:
        # if Auth API differs, ignore - safe fallback
        pass

    app = QtWidgets.QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())
