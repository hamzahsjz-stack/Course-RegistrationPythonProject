# TODO: Purpose: Purpose:
      #Secure login system with different roles.
      
      #Features:
      
      #Two roles: Student and Admin
      
      #Login with email/ID + password.
      
      #Passwords encrypted with bcrypt.
      
      #Redirect users to appropriate dashboards:
      
      #Students → registration panel.
      
      #Admins → course management panel.
      
      #Password recovery (email reset).
      #Database Table:
      
      #users


first code :

      from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import sqlite3
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = "secret123"
bcrypt = Bcrypt(app)

# =======================
# EMAIL CONFIG
# =======================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'k983emmm@gmail.com'
app.config['MAIL_PASSWORD'] = 'ewlyqbtsxoxhyquu'   # <-- replace with your Gmail App Password

mail = Mail(app)

# =======================
# DATABASE SETUP
# =======================
def init_db():
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                birthdate TEXT,
                national_id TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reset_tokens (
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
    print("✅ Database ready!")

init_db()

# =======================
# HELPERS
# =======================
def store_reset_token(email, token):
    created = datetime.utcnow().isoformat()
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reset_tokens (email, token, created_at) VALUES (?, ?, ?)",
                       (email, token, created))
        conn.commit()

def verify_reset_token(email, token, minutes_valid=15):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT token, created_at FROM reset_tokens WHERE email=? AND token=?", (email, token))
        row = cursor.fetchone()
        if not row:
            return False
        token_time = datetime.fromisoformat(row[1])
        if datetime.utcnow() - token_time > timedelta(minutes=minutes_valid):
            cursor.execute("DELETE FROM reset_tokens WHERE email=? AND token=?", (email, token))
            conn.commit()
            return False
        cursor.execute("DELETE FROM reset_tokens WHERE email=? AND token=?", (email, token))
        conn.commit()
        return True

def get_user_by_id(national_id):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email, password, role FROM users WHERE national_id=?", (national_id,))
        return cursor.fetchone()

def get_email_by_id(national_id):
    with sqlite3.connect("users.db") as conn:              # هذا سطر تخزين البيانات
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE national_id=?", (national_id,))
        row = cursor.fetchone()
        return row[0] if row else None

# =======================
# BOOTSTRAP BASE TEMPLATE
# =======================
bootstrap_base = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Secure Login</title>
    <!-- Bootstrap 5 CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body {{ background:#eafaf1; }}
      .card-bank {{ border-radius:14px; box-shadow:0 6px 18px rgba(0,0,0,0.08); }}
      .logo-circle {{ width:80px; height:80px; border-radius:50%; overflow:hidden; margin:auto; margin-bottom:15px; }}
      .logo-circle img {{ width:100%; height:100%; object-fit:cover; }}
      .btn-green {{ background:#28a745; color:white; border:none; }}
      .btn-green:hover {{ background:#218838; }}
      .small-muted {{ font-size:0.9rem; color:#6c757d; }}
      .no-decoration a {{ text-decoration:none; color:#28a745; }}
    </style>
  </head>
  <body>
    <div class="d-flex vh-100 align-items-center justify-content-center">
      <div class="card card-bank p-4" style="width:380px;">
        <div class="card-body">
          {content}
        </div>
      </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
"""

# =======================
# MAIN PAGE (login)
# =======================
@app.route('/', methods=['GET', 'POST'])
def home():
    message = ""
    if request.method == 'POST':
        national_id = request.form['national_id'].strip()
        password = request.form['password']
        user = get_user_by_id(national_id)
        if user and bcrypt.check_password_hash(user[1], password):
            session['user'] = user[0]
            session['role'] = user[2]
            return redirect(url_for('dashboard'))
        else:
            message = "Invalid ID or password."

    content = f"""
      <h3 class="text-center mb-3">Welcome</h3>
      <form method="POST" novalidate>
        <div class="mb-3">
          <label class="form-label">National ID</label>
          <input type="text" name="national_id" class="form-control" maxlength="10"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,10)" required>
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <div class="d-grid mb-2">
          <button class="btn btn-green" type="submit">Login</button>
        </div>
      </form>
      <div class="text-center mb-2 small-muted">{message}</div>
      <div class="d-flex justify-content-between no-decoration">
        <a href="/register">New User? Register</a>
        <a href="/forgot">Forgot Password?</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# =======================
# REGISTER PAGE
# =======================
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == 'POST':
        national_id = request.form['national_id'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        day = request.form['day']
        month = request.form['month']
        year = request.form['year']
        birthdate = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        role = 'student'

        if len(national_id) != 10 or not national_id.isdigit():
            message = "National ID must be exactly 10 digits."
        else:
            try:
                with sqlite3.connect("users.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (email, password, birthdate, national_id, role) VALUES (?, ?, ?, ?, ?)",
                                   (email, hashed_pw, birthdate, national_id, role))
                    conn.commit()
                session['user'] = email
                session['role'] = role
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                message = "Email or National ID already registered."

    content = f"""
      <div class="logo-circle">
        <img src="https://randomuser.me/api/portraits/men/75.jpg" alt="Avatar">
      </div>
      <h4 class="text-center mb-3">Create Account</h4>
      <form method="POST" novalidate>
        <div class="mb-2">
          <label class="form-label">National ID (10 digits)</label>
          <input type="text" name="national_id" class="form-control" maxlength="10"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,10)" required>
        </div>
        <div class="mb-2">
          <label class="form-label">Email</label>
          <input type="email" name="email" class="form-control" required>
        </div>
        <label class="form-label">Birthdate</label>
        <div class="d-flex gap-2 mb-3">
          <input type="text" name="day" placeholder="DD" maxlength="2" class="form-control" required
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,2)">
          <input type="text" name="month" placeholder="MM" maxlength="2" class="form-control" required
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,2)">
          <input type="text" name="year" placeholder="YYYY" maxlength="4" class="form-control" required
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,4)">
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Register</button>
        </div>
      </form>
      <div class="text-center mt-3 small-muted">{message}</div>
      <div class="text-center mt-2">
        <a href="/">Back to Login</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# =======================
# DASHBOARD
# =======================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    content = f"""
      <h4 class="text-center mb-3">Dashboard</h4>
      <p class="text-center"><strong>{session['user']}</strong></p>
      <div class="d-grid">
        <a class="btn btn-outline-success" href="/logout">Logout</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# =======================
# LOGOUT
# =======================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# =======================
# FORGOT PASSWORD
# =======================
@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    message = ""
    if request.method == 'POST':
        identifier = request.form['identifier'].strip()
        email = get_email_by_id(identifier)
        if email:
            code = f"{random.randint(0,999999):06d}"
            store_reset_token(email, code)
            html_body = f"""
            <div style="font-family:Arial,sans-serif; padding:20px;">
                <h2>Password Reset Request</h2>
                <p>Your password reset code is:</p>
                <p style="font-size:20px; letter-spacing:4px;"><strong>{code}</strong></p>
                <p>If you didn't request this, ignore this email.</p>
            </div>
            """
            msg = Message("Your Password Reset Code", sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Password reset code: {code}. Ignore if you didn't request this."
            msg.html = html_body
            mail.send(msg)
            session['reset_email'] = email
            return redirect(url_for('verify_code'))
        else:
            message = "No account found with this ID."
    content = f"""
      <h4 class="text-center mb-3">Forgot Password</h4>
      <form method="POST" novalidate>
        <div class="mb-3">
          <label class="form-label">National ID</label>
          <input type="text" name="identifier" class="form-control" maxlength="10"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,10)" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Send Reset Code</button>
        </div>
      </form>
      <div class="text-center mt-3 small-muted">{message}</div>
      <div class="text-center mt-2">
        <a href="/">Back to Login</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# =======================
# VERIFY CODE
# =======================
@app.route('/verify', methods=['GET', 'POST'])
def verify_code():
    message = ""
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        code = request.form['code'].strip()
        if verify_reset_token(email, code):
            session['verified'] = True
            return redirect(url_for('reset_password'))
        else:
            message = "Invalid or expired code."
    content = f"""
      <h4 class="text-center mb-3">Verify Code</h4>
      <form method="POST" novalidate>
        <div class="mb-3">
          <label class="form-label">6-digit Code</label>
          <input type="text" name="code" class="form-control" maxlength="6" pattern="\\d{{6}}"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,6)" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Verify</button>
        </div>
      </form>
      <div class="text-center mt-3 small-muted">{message}</div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# =======================
# RESET PASSWORD
# =======================
@app.route('/reset', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email or not session.get('verified'):
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        new_pw = request.form['password']
        hashed_pw = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed_pw, email))
            conn.commit()
        session.pop('reset_email', None)
        session.pop('verified', None)
        return redirect(url_for('home'))
    content = f"""
      <h4 class="text-center mb-3">Reset Password</h4>
      <form method="POST" novalidate>
        <div class="mb-3">
          <label class="form-label">New Password</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Update Password</button>
        </div>
      </form>
    """
    return render_template_string(bootstrap_base.format(content=content))

# =======================
# RUN SERVER
# =======================
if __name__ == '__main__':
    app.run(debug=True)

      #Database Table:
      
      #users


first code 

      
      #Example errors:
      
      #"Invalid ID or password"
      #"Email already registered" 

