## TO DO: Build the app frontend
    #GUI Design (PyQt5 or PyQt6)
    #You’ll make a GUI with:
    
    #Login screen
    
    #Admin dashboard
    
    #Add/edit courses
    
    #View reports
    
    #Student dashboard
    
    #Select courses
    
    #See timetable
    
    #View transcript
    
    #Use PyQt Designer or build it in code. The GUI connects to backend classes and database functions.
# Admin user :admin
# Admin password : admin
"""
Course Registration System - Frontend (PyQt5)
Enhanced Colored GUI Version 🎨
- Login screen (admin / student)
- Admin dashboard with blue theme
- Student dashboard with green theme
- Styled buttons, labels, and forms

Run:
    python course_registration_frontend.py
"""

import sys
import sqlite3
import hashlib
from typing import Dict
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QSpinBox, QCheckBox
)

DB_PATH = "course_registration.db"

# ----------------------------- Backend -----------------------------
class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            password_hash TEXT,
            role TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE,
            name TEXT,
            credits INTEGER,
            lecture_hours INTEGER,
            lab_hours INTEGER,
            max_capacity INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_user_id TEXT,
            course_code TEXT)''')

        self.conn.commit()
        if not self.get_user_by_id('admin'):
            self.add_user('admin', 'Administrator', 'admin@uni.edu', 'admin', 'admin')

    def add_user(self, user_id, name, email, password, role='student'):
        cur = self.conn.cursor()
        ph = hashlib.sha256(password.encode()).hexdigest()
        try:
            cur.execute("INSERT INTO users (user_id,name,email,password_hash,role) VALUES (?,?,?,?,?)",
                        (user_id, name, email, ph, role))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_by_id(self, user_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
        return cur.fetchone()

    def verify_user(self, user_id, password):
        row = self.get_user_by_id(user_id)
        if not row:
            return None
        ph = hashlib.sha256(password.encode()).hexdigest()
        if ph == row['password_hash']:
            return dict(row)
        return None

    def add_course(self, code, name, credits, lec, lab, cap):
        cur = self.conn.cursor()
        try:
            cur.execute('''INSERT INTO courses (course_code,name,credits,lecture_hours,lab_hours,max_capacity)
                           VALUES (?,?,?,?,?,?)''', (code, name, credits, lec, lab, cap))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_course(self, code, name, credits, lec, lab, cap):
        cur = self.conn.cursor()
        cur.execute('''UPDATE courses SET name=?, credits=?, lecture_hours=?, lab_hours=?, max_capacity=? WHERE course_code=?''',
                    (name, credits, lec, lab, cap, code))
        self.conn.commit()

    def delete_course(self, code):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM courses WHERE course_code=?', (code,))
        self.conn.commit()

    def list_courses(self):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM courses ORDER BY course_code')
        return [dict(r) for r in cur.fetchall()]

    def register_course(self, sid, code):
        cur = self.conn.cursor()
        cur.execute('SELECT COUNT(*) as c FROM registrations WHERE course_code=?', (code,))
        c = cur.fetchone()['c']
        cur.execute('SELECT * FROM courses WHERE course_code=?', (code,))
        course = cur.fetchone()
        if not course:
            return False, 'Not found'
        if c >= course['max_capacity']:
            return False, 'Full'
        cur.execute('SELECT * FROM registrations WHERE student_user_id=? AND course_code=?', (sid, code))
        if cur.fetchone():
            return False, 'Already registered'
        cur.execute('INSERT INTO registrations (student_user_id,course_code) VALUES (?,?)', (sid, code))
        self.conn.commit()
        return True, 'Registered'

    def drop_registration(self, sid, code):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM registrations WHERE student_user_id=? AND course_code=?', (sid, code))
        self.conn.commit()

    def get_registrations(self, sid):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM registrations WHERE student_user_id=?', (sid,))
        return [dict(r) for r in cur.fetchall()]

    def course_enrollment_counts(self):
        cur = self.conn.cursor()
        cur.execute('''SELECT c.course_code, c.name, c.max_capacity, COUNT(r.id) as enrolled
                       FROM courses c LEFT JOIN registrations r ON c.course_code = r.course_code
                       GROUP BY c.course_code, c.name, c.max_capacity''')
        return [dict(r) for r in cur.fetchall()]

# ----------------------------- GUI -----------------------------
class LoginWidget(QWidget):
    login_success = QtCore.pyqtSignal(dict)

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._build_ui()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet('''
            QWidget {background-color:#f4f7fa; font-family:'Segoe UI';}
            QLabel {font-size:14pt; color:#333; font-weight:600;}
            QLineEdit {border:1px solid #aaa; border-radius:6px; padding:4px; background:white;}
            QPushButton {background-color:#0078d7; color:white; border-radius:8px; padding:6px 12px;}
            QPushButton:hover {background-color:#005fa3;}
        ''')

    def _build_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Course Registration System")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        form.addRow('User ID:', self.username)
        form.addRow('Password:', self.password)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.login_btn = QPushButton('Login')
        self.register_btn = QPushButton('Create Student Account')
        btns.addWidget(self.login_btn); btns.addWidget(self.register_btn)
        layout.addLayout(btns)

        self.setLayout(layout)
        self.login_btn.clicked.connect(self.try_login)
        self.register_btn.clicked.connect(self.create_student_account)

    def try_login(self):
        uid = self.username.text().strip(); pwd = self.password.text().strip()
        user = self.db.verify_user(uid, pwd)
        if user:
            self.login_success.emit(user)
        else:
            QMessageBox.critical(self, 'Error', 'Invalid credentials')

    def create_student_account(self):
        uid = self.username.text().strip(); pwd = self.password.text().strip()
        if not uid or not pwd:
            QMessageBox.warning(self, 'Missing', 'Enter user id and password')
            return
        if self.db.get_user_by_id(uid):
            QMessageBox.warning(self, 'Exists', 'User already exists')
            return
        self.db.add_user(uid, uid, f'{uid}@uni.edu', pwd, 'student')
        QMessageBox.information(self, 'Success', 'Student created.')

class AdminDashboard(QWidget):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._build_ui()
        self._apply_style()
        self.load_courses()

    def _apply_style(self):
        self.setStyleSheet('''
            QWidget {background-color:#e9f3ff; font-family:'Segoe UI';}
            QLabel {color:#003366; font-weight:600; font-size:12pt;}
            QPushButton {background-color:#0052cc; color:white; border-radius:6px; padding:5px 10px;}
            QPushButton:hover {background-color:#003d99;}
            QTableWidget {background:white; gridline-color:#ccc; border-radius:6px;}
        ''')

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Admin Dashboard'))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Code','Name','Credits','Lecture','Lab','Capacity'])
        layout.addWidget(self.table)

        form = QFormLayout()
        self.course_code = QLineEdit(); self.course_name = QLineEdit()
        self.credits = QSpinBox(); self.credits.setRange(1,10)
        self.lecture = QSpinBox(); self.lab = QSpinBox(); self.capacity = QSpinBox(); self.capacity.setRange(1,500)
        form.addRow('Code:', self.course_code)
        form.addRow('Name:', self.course_name)
        form.addRow('Credits:', self.credits)
        form.addRow('Lecture:', self.lecture)
        form.addRow('Lab:', self.lab)
        form.addRow('Capacity:', self.capacity)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.add_btn = QPushButton('Add'); self.update_btn = QPushButton('Update'); self.delete_btn = QPushButton('Delete'); self.report_btn = QPushButton('Reports')
        for b in [self.add_btn, self.update_btn, self.delete_btn, self.report_btn]:
            btns.addWidget(b)
        layout.addLayout(btns)
        self.setLayout(layout)

        self.add_btn.clicked.connect(self.add_course)
        self.update_btn.clicked.connect(self.update_course)
        self.delete_btn.clicked.connect(self.delete_course)
        self.report_btn.clicked.connect(self.show_reports)
        self.table.cellClicked.connect(self.on_click)

    def load_courses(self):
        self.table.setRowCount(0)
        for c in self.db.list_courses():
            r = self.table.rowCount()
            self.table.insertRow(r)
            for i, k in enumerate(['course_code','name','credits','lecture_hours','lab_hours','max_capacity']):
                self.table.setItem(r,i,QTableWidgetItem(str(c[k])))

    def on_click(self,row,col):
        for i,(w) in enumerate([self.course_code,self.course_name,self.credits,self.lecture,self.lab,self.capacity]):
            if i<2:
                w.setText(self.table.item(row,i).text())
            else:
                w.setValue(int(self.table.item(row,i).text()))

    def add_course(self):
        ok = self.db.add_course(self.course_code.text().upper(),self.course_name.text(),self.credits.value(),self.lecture.value(),self.lab.value(),self.capacity.value())
        QMessageBox.information(self,'Result','Added' if ok else 'Duplicate'); self.load_courses()

    def update_course(self):
        self.db.update_course(self.course_code.text().upper(),self.course_name.text(),self.credits.value(),self.lecture.value(),self.lab.value(),self.capacity.value())
        QMessageBox.information(self,'Updated','Course updated'); self.load_courses()

    def delete_course(self):
        self.db.delete_course(self.course_code.text().upper()); QMessageBox.information(self,'Deleted','Course deleted'); self.load_courses()

    def show_reports(self):
        txt='Course Enrollments:\n\n'
        for r in self.db.course_enrollment_counts():
            txt+=f"{r['course_code']} - {r['enrolled']} / {r['max_capacity']}\n"
        QMessageBox.information(self,'Reports',txt)

class StudentDashboard(QWidget):
    def __init__(self, db: DatabaseManager, sid:str):
        super().__init__()
        self.db=db; self.sid=sid
        self._build_ui(); self._apply_style(); self.load_courses()

    def _apply_style(self):
        self.setStyleSheet('''
            QWidget {background-color:#f7fff7; font-family:'Segoe UI';}
            QLabel {color:#006600; font-weight:600; font-size:12pt;}
            QPushButton {background-color:#00aa00; color:white; border-radius:6px; padding:5px 10px;}
            QPushButton:hover {background-color:#007700;}
            QCheckBox {font-size:10pt; color:#333;}
        ''')

    def _build_ui(self):
        layout=QVBoxLayout(); layout.addWidget(QLabel(f'Student Dashboard - {self.sid}'))
        self.course_box=QVBoxLayout(); layout.addLayout(self.course_box)
        btns=QHBoxLayout();
        self.reg_btn=QPushButton('Register'); self.drop_btn=QPushButton('Drop'); self.refresh_btn=QPushButton('Refresh'); self.view_btn=QPushButton('View Enrolled')
        for b in [self.reg_btn,self.drop_btn,self.refresh_btn,self.view_btn]: btns.addWidget(b)
        layout.addLayout(btns); self.setLayout(layout)
        self.reg_btn.clicked.connect(self.register_selected); self.drop_btn.clicked.connect(self.drop_selected); self.refresh_btn.clicked.connect(self.load_courses); self.view_btn.clicked.connect(self.show_registered)

    def load_courses(self):
        for i in reversed(range(self.course_box.count())):
            w=self.course_box.itemAt(i).widget();
            if w: w.setParent(None)
        self.checks=[]; regs={r['course_code'] for r in self.db.get_registrations(self.sid)}
        for c in self.db.list_courses():
            cb=QCheckBox(f"{c['course_code']} - {c['name']} ({c['credits']} credits)"); cb.course_code=c['course_code']
            if c['course_code'] in regs: cb.setChecked(True)
            self.course_box.addWidget(cb); self.checks.append(cb)

    def register_selected(self):
        msg=[]
        for cb in self.checks:
            if cb.isChecked():
                ok,txt=self.db.register_course(self.sid,cb.course_code)
                msg.append(f"{cb.course_code}: {txt}")
        QMessageBox.information(self,'Result','\n'.join(msg)); self.load_courses()

    def drop_selected(self):
        for cb in self.checks:
            if cb.isChecked(): self.db.drop_registration(self.sid,cb.course_code)
        QMessageBox.information(self,'Dropped','Courses dropped'); self.load_courses()

    def show_registered(self):
        regs=self.db.get_registrations(self.sid)
        if not regs: QMessageBox.information(self,'None','No courses registered'); return
        txt='Registered Courses:\n\n'
        for r in regs: txt+=r['course_code']+'\n'
        QMessageBox.information(self,'Courses',txt)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db=DatabaseManager(); self.setWindowTitle('ECE Course Registration System'); self.resize(900,600)
        self.stack=QStackedWidget(); self.setCentralWidget(self.stack)
        self.login=LoginWidget(self.db); self.stack.addWidget(self.login)
        self.login.login_success.connect(self.on_login)

    def on_login(self,user:Dict):
        role=user['role']; uid=user['user_id']
        if role=='admin':
            self.admin=AdminDashboard(self.db)
            logout=QPushButton('Logout'); logout.clicked.connect(lambda:self.stack.setCurrentWidget(self.login))
            lay=QVBoxLayout(); lay.addWidget(self.admin); lay.addWidget(logout)
            c=QWidget(); c.setLayout(lay); self.stack.addWidget(c); self.stack.setCurrentWidget(c)
        else:
            self.student=StudentDashboard(self.db,uid)
            logout=QPushButton('Logout'); logout.clicked.connect(lambda:self.stack.setCurrentWidget(self.login))
            lay=QVBoxLayout(); lay.addWidget(self.student); lay.addWidget(logout)
            c=QWidget(); c.setLayout(lay); self.stack.addWidget(c); self.stack.setCurrentWidget(c)

if __name__=='__main__':
    app=QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec_())
