# ========================================
# IMPORTS
# ========================================
from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import sqlite3
from datetime import datetime, timedelta
import random

# ========================================
# APP & BCRYPT SETUP
# ========================================
app = Flask(__name__)
app.secret_key = "secret123"
bcrypt = Bcrypt(app)

# ========================================
# HARDCODED ADMIN LOGIN
# ========================================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ========================================
# EMAIL CONFIGURATION
# ========================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
# change here


mail = Mail(app)

# ========================================
# DATABASE SETUP
# ========================================
def init_db():
    """Create tables users and reset_tokens if they don't exist"""
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()

        # Users table
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

        # Reset password tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reset_tokens (
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
    print("✅ Database ready!")

init_db()

# ========================================
# HELPER FUNCTIONS
# ========================================
def store_reset_token(email, token):
    """Store reset code with timestamp"""
    created = datetime.utcnow().isoformat()
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reset_tokens (email, token, created_at) VALUES (?, ?, ?)",
                       (email, token, created))
        conn.commit()

def verify_reset_token(email, token, minutes_valid=15):
    """Check if the reset token is valid"""
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT token, created_at FROM reset_tokens WHERE email=? AND token=?",
                       (email, token))
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
    """Retrieve user data by National ID"""
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email, password, role FROM users WHERE national_id=?",
                       (national_id,))
        return cursor.fetchone()

def get_email_by_id(national_id):
    """Retrieve email of user by National ID"""
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE national_id=?", (national_id,))
        row = cursor.fetchone()
        return row[0] if row else None

# ========================================
# BOOTSTRAP BASE TEMPLATE
# ========================================
bootstrap_base = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Login Center</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body {{ background:#eafaf1; }}
      .card-bank {{ border-radius:14px; box-shadow:0 6px 18px rgba(0,0,0,0.08); }}
      .btn-green {{ background:#28a745; color:white; border:none; }}
      .btn-green:hover {{ background:#218838; }}
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
  </body>
</html>
"""

# ========================================
# STUDENT LOGIN PAGE
# ========================================
@app.route('/', methods=['GET', 'POST'])
def home():
    message = ""
    if request.method == "POST":
        national_id = request.form["national_id"].strip()
        password = request.form["password"]
        user = get_user_by_id(national_id)
        if user and bcrypt.check_password_hash(user[1], password):
            session["user"] = user[0]
            session["role"] = user[2]
            return redirect(url_for("dashboard"))
        else:
            message = "Invalid ID or password."

    content = f"""
      <h3 class="text-center mb-3">Welcome</h3>
      <form method="POST">
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
      <p class="text-danger text-center">{message}</p>
      <div class="d-flex justify-content-between no-decoration mb-3">
        <a href="/register">New User? Register</a>
        <a href="/forgot">Forgot Password?</a>
      </div>
      <div class="text-center">
        <a href="/admin" class="btn btn-outline-success btn-sm">Admin Login</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# ========================================
# REGISTER PAGE
# ========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == "POST":
        national_id = request.form["national_id"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        day = request.form["day"]
        month = request.form["month"]
        year = request.form["year"]
        birthdate = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        role = "student"

        if len(national_id) != 10 or not national_id.isdigit():
            message = "National ID must be exactly 10 digits."
        else:
            try:
                with sqlite3.connect("users.db") as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO users (email, password, birthdate, national_id, role)
                        VALUES (?, ?, ?, ?, ?)
                    """, (email, hashed_pw, birthdate, national_id, role))
                    conn.commit()
                session["user"] = email
                session["role"] = role
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                message = "Email or ID already registered."

    content = f"""
      <h3 class="text-center mb-3">Create Account</h3>
      <form method="POST">
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
          <input type="text" name="day" class="form-control" placeholder="DD" maxlength="2"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,2)" required>
          <input type="text" name="month" class="form-control" placeholder="MM" maxlength="2"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,2)" required>
          <input type="text" name="year" class="form-control" placeholder="YYYY" maxlength="4"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,4)" required>
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Register</button>
        </div>
      </form>
      <p class="text-danger text-center mt-2">{message}</p>
      <div class="text-center">
        <a href="/">Back to Login</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# ========================================
# STUDENT DASHBOARD
# ========================================
@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))
    content = f"""
      <h3 class="text-center mb-3">Dashboard</h3>
      <p class="text-center">Logged in as <strong>{session['user']}</strong></p>
      <div class="d-grid">
        <a class="btn btn-outline-success" href="/logout">Logout</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home"))

# ========================================
# ADMIN LOGIN PAGE
# ========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    message = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            message = "Invalid admin credentials."

    content = f"""
      <h3 class="text-center mb-3">Admin Login</h3>
      <form method="POST">
        <div class="mb-3">
          <label class="form-label">Username</label>
          <input type="text" name="username" class="form-control" required>
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Login</button>
        </div>
      </form>
      <p class="text-danger text-center mt-2">{message}</p>
      <div class="text-center mt-2">
        <a href="/">Back</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# ========================================
# ADMIN DASHBOARD
# ========================================
@app.route('/admin/dashboard')
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    content = """
      <h3 class="text-center mb-3">Admin Dashboard</h3>
      <p class="text-center">Welcome, Administrator!</p>
      <div class="d-grid">
        <a class="btn btn-outline-success" href="/logout_admin">Logout Admin</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

@app.route('/logout_admin')
def logout_admin():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

# ========================================
# FORGOT PASSWORD
# ========================================
@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    message = ""
    if request.method == "POST":
        identifier = request.form["identifier"].strip()
        email = get_email_by_id(identifier)
        if email:
            code = f"{random.randint(0,999999):06d}"
            store_reset_token(email, code)
            html_body = f"""
            <div style="font-family:Arial; padding:20px;">
                <h2>Password Reset</h2>
                <p>Your reset code:</p>
                <h2>{code}</h2>
                <p>If this wasn't you, ignore this email.</p>
            </div>
            """
            msg = Message("Password Reset Code",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.html = html_body
            msg.body = f"Your reset code is {code}."
            mail.send(msg)
            session["reset_email"] = email
            return redirect(url_for("verify_code"))
        else:
            message = "No account found with this ID."

    content = f"""
      <h3 class="text-center mb-3">Forgot Password</h3>
      <form method="POST">
        <div class="mb-3">
          <label class="form-label">National ID</label>
          <input type="text" name="identifier" class="form-control" maxlength="10"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,10)" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Send Code</button>
        </div>
      </form>
      <p class="text-danger text-center mt-2">{message}</p>
      <div class="text-center mt-2">
        <a href="/">Back to Login</a>
      </div>
    """
    return render_template_string(bootstrap_base.format(content=content))

# ========================================
# VERIFY RESET CODE
# ========================================
@app.route('/verify', methods=['GET', 'POST'])
def verify_code():
    email = session.get("reset_email")
    if not email:
        return redirect(url_for("forgot_password"))
    message = ""
    if request.method == "POST":
        code = request.form["code"].strip()
        if verify_reset_token(email, code):
            session["verified"] = True
            return redirect(url_for("reset_password"))
        else:
            message = "Invalid or expired code."
    content = f"""
      <h3 class="text-center mb-3">Verify Code</h3>
      <form method="POST">
        <div class="mb-3">
          <label class="form-label">6-digit Code</label>
          <input type="text" name="code" class="form-control" maxlength="6"
                 oninput="this.value=this.value.replace(/[^0-9]/g,'').slice(0,6)" required>
        </div>
        <div class="d-grid">
          <button class="btn btn-green" type="submit">Verify</button>
        </div>
      </form>
      <p class="text-danger text-center mt-2">{message}</p>
    """
    return render_template_string(bootstrap_base.format(content=content))

# ========================================
# RESET PASSWORD PAGE
# ========================================
@app.route('/reset', methods=['GET', 'POST'])
def reset_password():
    email = session.get("reset_email")
    verified = session.get("verified")
    if not email or not verified:
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        new_pw = request.form["password"]
        hashed_pw = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password=? WHERE email=?",
                           (hashed_pw, email))
            conn.commit()
        session.pop("reset_email", None)
        session.pop("verified", None)
        return redirect(url_for("home"))
    content = f"""
      <h3 class="text-center mb-3">Reset Password</h3>
      <form method="POST">
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

# ========================================
# RUN SERVER
# ========================================
if __name__ == "__main__":
    app.run(debug=True)
