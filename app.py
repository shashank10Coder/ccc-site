"""
==============================================================
CHANAKYA COMPETITION CRACKER (CCC) - MAIN BACKEND SERVER
==============================================================

Run locally:
    python app.py

Website:
    http://localhost:5000

Email OTP:
    Uses Resend API instead of Gmail SMTP.

Required environment variables for Resend:
    RESEND_API_KEY=re_xxxxxxxxxxxxxxxxx
    EMAIL_FROM=onboarding@resend.dev

Other environment variables:
    SECRET_KEY=your-secret-key
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=your-admin-password
    SUPPORT_EMAIL=your-email@example.com
    PAYMENTS_ENABLED=false
    DEBUG_MODE=true
    PORT=5000
"""

import os
import json
import random
import string
import time
from datetime import datetime
from functools import wraps

import requests

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_from_directory,
    abort,
    flash,
)

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from dotenv import load_dotenv
except ImportError:
    print("\n[SETUP NEEDED] python-dotenv is not installed.")
    print("Run: pip install -r requirements.txt\n")
    raise

load_dotenv()


# ==============================================================
# SECTION 1 - SETUP & CONFIGURATION
# ==============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_PDF_DIR = os.path.join(BASE_DIR, "static", "uploads", "pdfs")
UPLOAD_BLOG_IMG_DIR = os.path.join(BASE_DIR, "static", "uploads", "blog_images")
UPLOAD_PROFILE_DIR = os.path.join(BASE_DIR, "static", "uploads", "profile_pics")

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-me")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

SUPPORT_EMAIL = os.getenv(
    "SUPPORT_EMAIL",
    "ChanakyaCompititionCracker.Business@gmail.com"
)

PAYMENTS_ENABLED = (
    os.getenv("PAYMENTS_ENABLED", "false").lower() == "true"
)

DEBUG_MODE = (
    os.getenv("DEBUG_MODE", "true").lower() == "true"
)

PORT = int(os.getenv("PORT", "5000"))

# --------------------------------------------------------------
# RESEND EMAIL CONFIGURATION
# --------------------------------------------------------------

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    "onboarding@resend.dev"
).strip()

RESEND_API_URL = "https://api.resend.com/emails"


ALLOWED_PDF_EXT = {"pdf"}
ALLOWED_IMG_EXT = {"png", "jpg", "jpeg", "webp", "svg"}


# In-memory OTP store
#
# {
#   "email@example.com": {
#       "otp": "123456",
#       "expires": timestamp,
#       "purpose": "signup",
#       "data": {...}
#   }
# }
#
# OTPs disappear if the server restarts.

PENDING_OTPS = {}


# Make sure required directories exist.
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_PDF_DIR, exist_ok=True)
os.makedirs(UPLOAD_BLOG_IMG_DIR, exist_ok=True)
os.makedirs(UPLOAD_PROFILE_DIR, exist_ok=True)


# ==============================================================
# SECTION 2 - SMALL HELPER FUNCTIONS
# ==============================================================

def read_json(filename):
    """Read a JSON file from the /data folder."""

    path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        return json.loads(content) if content else []

    except (json.JSONDecodeError, OSError) as e:
        print(f"[JSON READ ERROR] {filename}: {e}")
        return []


def write_json(filename, data):
    """Save data to a JSON file inside /data."""

    path = os.path.join(DATA_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def allowed_file(filename, allowed_set):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_set
    )


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


def generate_id(prefix):
    """Make a simple unique ID like pdf-a1b2c3."""

    return f"{prefix}-{int(time.time() * 1000)}"


def current_user():
    """Return the logged-in user's full record, or None."""

    if "user_email" not in session:
        return None

    users = read_json("users.json")

    for user in users:
        if user.get("email") == session["user_email"]:
            return user

    return None


def login_required(view_func):

    @wraps(view_func)
    def wrapped(*args, **kwargs):

        if not current_user():
            flash("Please log in to continue.", "error")

            return redirect(
                url_for(
                    "login_page",
                    next=request.path
                )
            )

        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):

    @wraps(view_func)
    def wrapped(*args, **kwargs):

        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))

        return view_func(*args, **kwargs)

    return wrapped


# ==============================================================
# SECTION 3 - EMAIL (OTP) USING RESEND API
# ==============================================================

def send_otp_email(to_email, otp_code, purpose="verification"):
    """
    Send OTP using Resend API.

    Environment variables:

        RESEND_API_KEY
        EMAIL_FROM
    """

    subject = f"Your CCC {purpose} code"

    text_body = (
        f"Your Chanakya Competition Cracker verification code is: "
        f"{otp_code}\n\n"
        f"This code expires in 10 minutes. "
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"- Team CCC"
    )

    html_body = f"""
    <div style="
        font-family: Arial, sans-serif;
        max-width: 600px;
        margin: 0 auto;
        padding: 30px;
        background: #f7f7f7;
    ">

        <div style="
            background: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
        ">

            <h2 style="margin-bottom: 10px;">
                Chanakya Competition Cracker
            </h2>

            <p>
                Your verification code is:
            </p>

            <div style="
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 8px;
                margin: 25px 0;
            ">
                {otp_code}
            </div>

            <p>
                This code expires in <strong>10 minutes</strong>.
            </p>

            <p style="color: #777; font-size: 13px;">
                If you did not request this code, you can safely ignore
                this email.
            </p>

            <p>
                — Team CCC
            </p>

        </div>

    </div>
    """

    # ----------------------------------------------------------
    # Check Resend configuration
    # ----------------------------------------------------------

    if not RESEND_API_KEY:
        print("\n[RESEND ERROR] RESEND_API_KEY is missing.")
        print(f"[DEV OTP] {to_email} -> {otp_code}\n")

        # Returning False lets the caller know email wasn't sent.
        return False

    if not EMAIL_FROM:
        print("\n[RESEND ERROR] EMAIL_FROM is missing.")
        print(f"[DEV OTP] {to_email} -> {otp_code}\n")

        return False

    # ----------------------------------------------------------
    # Send email through Resend
    # ----------------------------------------------------------

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:

        response = requests.post(
            RESEND_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )

        # Success
        if 200 <= response.status_code < 300:

            try:
                result = response.json()
            except ValueError:
                result = {}

            print(
                f"[EMAIL SENT] OTP sent to {to_email}. "
                f"Resend ID: {result.get('id', 'unknown')}"
            )

            return True

        # Resend returned an error
        print(
            f"[RESEND ERROR] HTTP {response.status_code}: "
            f"{response.text}"
        )

        return False

    except requests.exceptions.Timeout:

        print(
            "[RESEND ERROR] Request timed out while contacting Resend."
        )

        return False

    except requests.exceptions.RequestException as e:

        print(
            f"[RESEND ERROR] Network/request error: {e}"
        )

        return False

    except Exception as e:

        print(
            f"[RESEND ERROR] Unexpected error: {e}"
        )

        return False


# ==============================================================
# SECTION 4 - PUBLIC PAGES
# ==============================================================

@app.context_processor
def inject_globals():

    return {
        "logged_in_user": current_user(),
        "support_email": SUPPORT_EMAIL,
        "payments_enabled": PAYMENTS_ENABLED,
        "site_name": "Chanakya Competition Cracker",
    }


@app.route("/")
def home():

    blogs = sorted(
        read_json("blogs.json"),
        key=lambda b: b.get("publish_date", ""),
        reverse=True
    )[:3]

    pdfs = sorted(
        read_json("pdfs.json"),
        key=lambda p: p.get("upload_date", ""),
        reverse=True
    )[:3]

    return render_template(
        "home.html",
        latest_blogs=blogs,
        latest_pdfs=pdfs
    )


@app.route("/mcqs")
def mcqs_page():

    sets = read_json("mcqs.json")

    category = request.args.get("category")

    if category:
        sets = [
            s for s in sets
            if s.get("category") == category
        ]

    categories = sorted(
        set(
            s.get("category", "General")
            for s in read_json("mcqs.json")
        )
    )

    return render_template(
        "mcqs.html",
        mcq_sets=sets,
        categories=categories,
        active_category=category
    )


@app.route("/mcqs/<set_id>")
def mcq_attempt(set_id):

    sets = read_json("mcqs.json")

    mcq_set = next(
        (s for s in sets if s.get("id") == set_id),
        None
    )

    if not mcq_set:
        abort(404)

    if mcq_set.get("is_paid"):

        user = current_user()

        purchases = read_json("purchases.json")

        owns_it = bool(
            user and any(
                p.get("user_email") == user.get("email")
                and p.get("item_id") == set_id
                for p in purchases
            )
        )

        if not owns_it:

            return render_template(
                "locked.html",
                item=mcq_set,
                item_kind="MCQ set",
                back_url=url_for("mcqs_page")
            )

    return render_template(
        "mcq_attempt.html",
        mcq_set=mcq_set
    )


@app.route("/blog")
def blog_page():

    blogs = sorted(
        read_json("blogs.json"),
        key=lambda b: b.get("publish_date", ""),
        reverse=True
    )

    category = request.args.get("category")

    if category:
        blogs = [
            b for b in blogs
            if b.get("category") == category
        ]

    categories = sorted(
        set(
            b.get("category", "General")
            for b in read_json("blogs.json")
        )
    )

    return render_template(
        "blog.html",
        blogs=blogs,
        categories=categories,
        active_category=category
    )


@app.route("/blog/<blog_id>")
def blog_detail(blog_id):

    blogs = read_json("blogs.json")

    post = next(
        (b for b in blogs if b.get("id") == blog_id),
        None
    )

    if not post:
        abort(404)

    if post.get("is_paid"):

        user = current_user()

        purchases = read_json("purchases.json")

        owns_it = bool(
            user and any(
                p.get("user_email") == user.get("email")
                and p.get("item_id") == blog_id
                for p in purchases
            )
        )

        if not owns_it:

            return render_template(
                "locked.html",
                item=post,
                item_kind="blog article",
                back_url=url_for("blog_page")
            )

    for blog in blogs:

        if blog.get("id") == blog_id:

            blog["views"] = blog.get("views", 0) + 1

    write_json("blogs.json", blogs)

    return render_template(
        "blog_detail.html",
        post=post
    )


@app.route("/pdfs")
def pdfs_page():

    pdfs = sorted(
        read_json("pdfs.json"),
        key=lambda p: p.get("upload_date", ""),
        reverse=True
    )

    category = request.args.get("category")
    ptype = request.args.get("type")

    if category:
        pdfs = [
            p for p in pdfs
            if p.get("category") == category
        ]

    if ptype:
        pdfs = [
            p for p in pdfs
            if p.get("type") == ptype
        ]

    categories = sorted(
        set(
            p.get("category", "General")
            for p in read_json("pdfs.json")
        )
    )

    return render_template(
        "pdfs.html",
        pdfs=pdfs,
        categories=categories,
        active_category=category,
        active_type=ptype
    )


@app.route("/pdfs/<pdf_id>")
def pdf_detail(pdf_id):

    pdfs = read_json("pdfs.json")

    pdf = next(
        (p for p in pdfs if p.get("id") == pdf_id),
        None
    )

    if not pdf:
        abort(404)

    owns_it = False

    if pdf.get("is_paid"):

        user = current_user()

        purchases = read_json("purchases.json")

        owns_it = bool(
            user and any(
                p.get("user_email") == user.get("email")
                and p.get("item_id") == pdf_id
                for p in purchases
            )
        )

    else:
        owns_it = True

    return render_template(
        "pdf_detail.html",
        pdf=pdf,
        owns_it=owns_it
    )


@app.route("/questions")
def questions_page():

    questions = sorted(
        read_json("questions.json"),
        key=lambda q: q.get("date", ""),
        reverse=True
    )

    return render_template(
        "questions.html",
        questions=questions
    )


@app.route("/questions/<question_id>")
def question_detail(question_id):

    questions = read_json("questions.json")

    q = next(
        (x for x in questions if x.get("id") == question_id),
        None
    )

    if not q:
        abort(404)

    return render_template(
        "question_detail.html",
        question=q
    )


@app.route("/questions/ask", methods=["POST"])
@login_required
def ask_question():

    questions = read_json("questions.json")

    user = current_user()

    new_q = {
        "id": generate_id("q"),
        "title": request.form.get("title", "").strip(),
        "body": request.form.get("body", "").strip(),
        "category": request.form.get(
            "category",
            "General"
        ).strip(),
        "asked_by": user["name"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "answers": []
    }

    if not new_q["title"] or not new_q["body"]:

        flash(
            "Please fill in both a title and details for your question.",
            "error"
        )

        return redirect(url_for("questions_page"))

    questions.append(new_q)

    write_json(
        "questions.json",
        questions
    )

    flash(
        "Your question has been posted.",
        "success"
    )

    return redirect(
        url_for(
            "question_detail",
            question_id=new_q["id"]
        )
    )


@app.route(
    "/questions/<question_id>/answer",
    methods=["POST"]
)
@login_required
def answer_question(question_id):

    questions = read_json("questions.json")

    user = current_user()

    q = next(
        (x for x in questions if x.get("id") == question_id),
        None
    )

    if not q:
        abort(404)

    body = request.form.get("body", "").strip()

    if body:

        q.setdefault("answers", []).append({
            "answered_by": user["name"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "body": body
        })

        write_json(
            "questions.json",
            questions
        )

        flash(
            "Your answer has been posted.",
            "success"
        )

    return redirect(
        url_for(
            "question_detail",
            question_id=question_id
        )
    )


@app.route("/help")
def help_page():
    return render_template("help.html")


# ==============================================================
# SECTION 5 - AUTH
# ==============================================================

@app.route("/signup", methods=["GET", "POST"])
def signup_page():

    if request.method == "GET":

        return render_template("signup.html")

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not name or not email or not password:

        flash(
            "Please fill in all fields.",
            "error"
        )

        return redirect(
            url_for("signup_page")
        )

    users = read_json("users.json")

    if any(
        u.get("email") == email
        for u in users
    ):

        flash(
            "An account with this email already exists. "
            "Please log in instead.",
            "error"
        )

        return redirect(
            url_for("login_page")
        )

    otp = generate_otp()

    PENDING_OTPS[email] = {
        "otp": otp,
        "expires": time.time() + 600,
        "purpose": "signup",
        "data": {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(
                password
            ),
        }
    }

    email_sent = send_otp_email(
        email,
        otp,
        purpose="signup verification"
    )

    session["otp_pending_email"] = email

    if email_sent:

        flash(
            "We've sent a 6-digit code to your email. "
            "Enter it below to finish creating your account.",
            "info"
        )

    else:

        flash(
            "We couldn't send the verification email right now. "
            "Please check the email configuration.",
            "error"
        )

    return redirect(
        url_for("verify_otp_page")
    )


@app.route("/login", methods=["GET", "POST"])
def login_page():

    if request.method == "GET":

        return render_template("login.html")

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    users = read_json("users.json")

    user = next(
        (
            u for u in users
            if u.get("email") == email
        ),
        None
    )

    if (
        not user
        or not check_password_hash(
            user.get("password_hash", ""),
            password
        )
    ):

        flash(
            "Incorrect email or password.",
            "error"
        )

        return redirect(
            url_for("login_page")
        )

    otp = generate_otp()

    PENDING_OTPS[email] = {
        "otp": otp,
        "expires": time.time() + 600,
        "purpose": "login",
        "data": {}
    }

    email_sent = send_otp_email(
        email,
        otp,
        purpose="login verification"
    )

    session["otp_pending_email"] = email

    if email_sent:

        flash(
            "We've sent a 6-digit code to your email "
            "to confirm it's you.",
            "info"
        )

    else:

        flash(
            "We couldn't send the verification email right now. "
            "Please check the email configuration.",
            "error"
        )

    return redirect(
        url_for("verify_otp_page")
    )


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp_page():

    email = session.get(
        "otp_pending_email"
    )

    if not email:

        return redirect(
            url_for("login_page")
        )

    if request.method == "GET":

        return render_template(
            "verify_otp.html",
            email=email
        )

    entered_otp = request.form.get(
        "otp",
        ""
    ).strip()

    record = PENDING_OTPS.get(email)

    if (
        not record
        or time.time() > record["expires"]
    ):

        flash(
            "This code has expired. Please try again.",
            "error"
        )

        return redirect(
            url_for("login_page")
        )

    if entered_otp != record["otp"]:

        flash(
            "That code was incorrect. Please check and try again.",
            "error"
        )

        return redirect(
            url_for("verify_otp_page")
        )

    # ----------------------------------------------------------
    # OTP CORRECT
    # ----------------------------------------------------------

    if record["purpose"] == "signup":

        users = read_json("users.json")

        new_user = {
            "email": record["data"]["email"],
            "name": record["data"]["name"],
            "password_hash": record["data"]["password_hash"],
            "bio": "",
            "profile_pic": "/static/img/placeholders/default-avatar.svg",
            "joined": datetime.now().strftime("%Y-%m-%d"),
        }

        users.append(new_user)

        write_json(
            "users.json",
            users
        )

    del PENDING_OTPS[email]

    session.pop(
        "otp_pending_email",
        None
    )

    session["user_email"] = email

    flash(
        "Welcome to Chanakya Competition Cracker.",
        "success"
    )

    return redirect(
        url_for("home")
    )


@app.route("/resend-otp", methods=["POST"])
def resend_otp():

    email = session.get(
        "otp_pending_email"
    )

    if (
        not email
        or email not in PENDING_OTPS
    ):

        return jsonify({
            "ok": False,
            "message": "No pending verification found."
        }), 400

    otp = generate_otp()

    PENDING_OTPS[email]["otp"] = otp

    PENDING_OTPS[email]["expires"] = (
        time.time() + 600
    )

    email_sent = send_otp_email(
        email,
        otp,
        purpose="verification"
    )

    if not email_sent:

        return jsonify({
            "ok": False,
            "message": "Could not send the email. Please try again."
        }), 500

    return jsonify({
        "ok": True,
        "message": "A new code has been sent."
    })


@app.route("/logout")
def logout():

    session.pop(
        "user_email",
        None
    )

    flash(
        "You have been logged out.",
        "info"
    )

    return redirect(
        url_for("home")
    )


# ==============================================================
# SECTION 6 - STUDENT PROFILE & PURCHASES
# ==============================================================

@app.route("/profile")
@login_required
def profile_page():

    user = current_user()

    purchases = [
        p for p in read_json("purchases.json")
        if p.get("user_email") == user.get("email")
    ]

    pdfs = read_json("pdfs.json")
    blogs = read_json("blogs.json")
    mcqs = read_json("mcqs.json")

    purchased_pdfs = [
        p for p in pdfs
        if any(
            pu.get("item_id") == p.get("id")
            for pu in purchases
        )
    ]

    purchased_blogs = [
        b for b in blogs
        if any(
            pu.get("item_id") == b.get("id")
            for pu in purchases
        )
    ]

    purchased_mcqs = [
        m for m in mcqs
        if any(
            pu.get("item_id") == m.get("id")
            for pu in purchases
        )
    ]

    return render_template(
        "profile.html",
        user=user,
        purchased_pdfs=purchased_pdfs,
        purchased_blogs=purchased_blogs,
        purchased_mcqs=purchased_mcqs
    )


@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():

    user = current_user()

    users = read_json("users.json")

    new_name = request.form.get(
        "name",
        ""
    ).strip()

    new_bio = request.form.get(
        "bio",
        ""
    ).strip()

    for u in users:

        if u.get("email") == user.get("email"):

            if new_name:
                u["name"] = new_name

            u["bio"] = new_bio

            file = request.files.get(
                "profile_pic"
            )

            if (
                file
                and file.filename
                and allowed_file(
                    file.filename,
                    ALLOWED_IMG_EXT
                )
            ):

                filename = secure_filename(
                    f"{user['email'].split('@')[0]}_"
                    f"{int(time.time())}_"
                    f"{file.filename}"
                )

                file.save(
                    os.path.join(
                        UPLOAD_PROFILE_DIR,
                        filename
                    )
                )

                u["profile_pic"] = (
                    f"/static/uploads/profile_pics/{filename}"
                )

    write_json(
        "users.json",
        users
    )

    flash(
        "Your profile has been updated.",
        "success"
    )

    return redirect(
        url_for("profile_page")
    )


# ==============================================================
# SECTION 7 - ADMIN PANEL
# ==============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "GET":

        return render_template(
            "admin/login.html"
        )

    username = request.form.get(
        "username",
        ""
    )

    password = request.form.get(
        "password",
        ""
    )

    if (
        username == ADMIN_USERNAME
        and password == ADMIN_PASSWORD
    ):

        session["is_admin"] = True

        return redirect(
            url_for("admin_dashboard")
        )

    flash(
        "Incorrect admin username or password.",
        "error"
    )

    return redirect(
        url_for("admin_login")
    )


@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "is_admin",
        None
    )

    return redirect(
        url_for("admin_login")
    )


@app.route("/admin")
@admin_required
def admin_dashboard():

    stats = {
        "users": len(read_json("users.json")),
        "pdfs": len(read_json("pdfs.json")),
        "blogs": len(read_json("blogs.json")),
        "mcq_sets": len(read_json("mcqs.json")),
        "questions": len(read_json("questions.json")),
        "purchases": len(read_json("purchases.json")),
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats
    )


@app.route("/admin/pdfs", methods=["GET", "POST"])
@admin_required
def admin_pdfs():

    if request.method == "POST":

        pdfs = read_json("pdfs.json")

        pdf_file = request.files.get(
            "pdf_file"
        )

        cover_file = request.files.get(
            "cover_image"
        )

        if (
            not pdf_file
            or not allowed_file(
                pdf_file.filename,
                ALLOWED_PDF_EXT
            )
        ):

            flash(
                "Please choose a valid PDF file to upload.",
                "error"
            )

            return redirect(
                url_for("admin_pdfs")
            )

        new_id = generate_id("pdf")

        pdf_filename = secure_filename(
            f"{new_id}_{pdf_file.filename}"
        )

        pdf_file.save(
            os.path.join(
                UPLOAD_PDF_DIR,
                pdf_filename
            )
        )

        cover_path = (
            "/static/img/placeholders/pdf-cover-1.svg"
        )

        if (
            cover_file
            and cover_file.filename
            and allowed_file(
                cover_file.filename,
                ALLOWED_IMG_EXT
            )
        ):

            cover_filename = secure_filename(
                f"{new_id}_{cover_file.filename}"
            )

            cover_file.save(
                os.path.join(
                    UPLOAD_BLOG_IMG_DIR,
                    cover_filename
                )
            )

            cover_path = (
                f"/static/uploads/blog_images/{cover_filename}"
            )

        is_paid = (
            request.form.get("is_paid") == "on"
        )

        pdfs.append({

            "id": new_id,

            "title": request.form.get(
                "title",
                ""
            ).strip(),

            "description": request.form.get(
                "description",
                ""
            ).strip(),

            "category": request.form.get(
                "category",
                "General"
            ).strip(),

            "type": request.form.get(
                "type",
                "MCQ PDF"
            ),

            "is_paid": is_paid,

            "price": (
                int(
                    request.form.get(
                        "price",
                        0
                    ) or 0
                )
                if is_paid
                else 0
            ),

            "cover_image": cover_path,

            "file_name": pdf_filename,

            "upload_date": datetime.now().strftime(
                "%Y-%m-%d"
            ),

            "downloads": 0
        })

        write_json(
            "pdfs.json",
            pdfs
        )

        flash(
            "PDF uploaded successfully.",
            "success"
        )

        return redirect(
            url_for("admin_pdfs")
        )

    pdfs = sorted(
        read_json("pdfs.json"),
        key=lambda p: p.get("upload_date", ""),
        reverse=True
    )

    return render_template(
        "admin/pdfs.html",
        pdfs=pdfs
    )


@app.route(
    "/admin/pdfs/<pdf_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_pdf(pdf_id):

    pdfs = read_json("pdfs.json")

    target = next(
        (
            p for p in pdfs
            if p.get("id") == pdf_id
        ),
        None
    )

    if target:

        file_path = os.path.join(
            UPLOAD_PDF_DIR,
            target.get("file_name", "")
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        pdfs = [
            p for p in pdfs
            if p.get("id") != pdf_id
        ]

        write_json(
            "pdfs.json",
            pdfs
        )

        flash(
            "PDF removed.",
            "success"
        )

    return redirect(
        url_for("admin_pdfs")
    )


@app.route(
    "/admin/blogs",
    methods=["GET", "POST"]
)
@admin_required
def admin_blogs():

    if request.method == "POST":

        blogs = read_json("blogs.json")

        new_id = generate_id("blog")

        cover_path = (
            "/static/img/placeholders/blog-cover-1.svg"
        )

        cover_file = request.files.get(
            "cover_image"
        )

        if (
            cover_file
            and cover_file.filename
            and allowed_file(
                cover_file.filename,
                ALLOWED_IMG_EXT
            )
        ):

            cover_filename = secure_filename(
                f"{new_id}_{cover_file.filename}"
            )

            cover_file.save(
                os.path.join(
                    UPLOAD_BLOG_IMG_DIR,
                    cover_filename
                )
            )

            cover_path = (
                f"/static/uploads/blog_images/{cover_filename}"
            )

        is_paid = (
            request.form.get("is_paid") == "on"
        )

        blogs.append({

            "id": new_id,

            "title": request.form.get(
                "title",
                ""
            ).strip(),

            "summary": request.form.get(
                "summary",
                ""
            ).strip(),

            "content": request.form.get(
                "content",
                ""
            ).strip(),

            "category": request.form.get(
                "category",
                "General"
            ).strip(),

            "is_paid": is_paid,

            "price": (
                int(
                    request.form.get(
                        "price",
                        0
                    ) or 0
                )
                if is_paid
                else 0
            ),

            "cover_image": cover_path,

            "author": "CCC Editorial Desk",

            "publish_date": datetime.now().strftime(
                "%Y-%m-%d"
            ),

            "views": 0
        })

        write_json(
            "blogs.json",
            blogs
        )

        flash(
            "Blog post published.",
            "success"
        )

        return redirect(
            url_for("admin_blogs")
        )

    blogs = sorted(
        read_json("blogs.json"),
        key=lambda b: b.get("publish_date", ""),
        reverse=True
    )

    return render_template(
        "admin/blogs.html",
        blogs=blogs
    )


@app.route(
    "/admin/blogs/<blog_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_blog(blog_id):

    blogs = read_json("blogs.json")

    blogs = [
        b for b in blogs
        if b.get("id") != blog_id
    ]

    write_json(
        "blogs.json",
        blogs
    )

    flash(
        "Blog post removed.",
        "success"
    )

    return redirect(
        url_for("admin_blogs")
    )


@app.route(
    "/admin/mcqs",
    methods=["GET", "POST"]
)
@admin_required
def admin_mcqs():

    if request.method == "POST":

        mcq_sets = read_json("mcqs.json")

        questions = []

        q_texts = request.form.getlist(
            "question_text[]"
        )

        q_options = request.form.getlist(
            "question_options[]"
        )

        q_answers = request.form.getlist(
            "question_answer[]"
        )

        q_explanations = request.form.getlist(
            "question_explanation[]"
        )

        for i in range(len(q_texts)):

            if not q_texts[i].strip():
                continue

            options = [
                o.strip()
                for o in q_options[i].split(",")
                if o.strip()
            ]

            answer = 0

            if (
                i < len(q_answers)
                and q_answers[i].isdigit()
            ):
                answer = int(q_answers[i])

            explanation = ""

            if i < len(q_explanations):
                explanation = (
                    q_explanations[i].strip()
                )

            questions.append({

                "q": q_texts[i].strip(),

                "options": options,

                "answer": answer,

                "explanation": explanation
            })

        is_paid = (
            request.form.get("is_paid") == "on"
        )

        mcq_sets.append({

            "id": generate_id("mcq-set"),

            "title": request.form.get(
                "title",
                ""
            ).strip(),

            "category": request.form.get(
                "category",
                "General"
            ).strip(),

            "is_paid": is_paid,

            "price": (
                int(
                    request.form.get(
                        "price",
                        0
                    ) or 0
                )
                if is_paid
                else 0
            ),

            "questions": questions
        })

        write_json(
            "mcqs.json",
            mcq_sets
        )

        flash(
            "MCQ set created.",
            "success"
        )

        return redirect(
            url_for("admin_mcqs")
        )

    mcq_sets = read_json("mcqs.json")

    return render_template(
        "admin/mcqs.html",
        mcq_sets=mcq_sets
    )


@app.route(
    "/admin/mcqs/<set_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_mcq(set_id):

    mcq_sets = read_json("mcqs.json")

    mcq_sets = [
        s for s in mcq_sets
        if s.get("id") != set_id
    ]

    write_json(
        "mcqs.json",
        mcq_sets
    )

    flash(
        "MCQ set removed.",
        "success"
    )

    return redirect(
        url_for("admin_mcqs")
    )


@app.route("/admin/users")
@admin_required
def admin_users():

    users = read_json("users.json")

    return render_template(
        "admin/users.html",
        users=users
    )


@app.route("/admin/questions")
@admin_required
def admin_questions():

    questions = read_json(
        "questions.json"
    )

    return render_template(
        "admin/questions.html",
        questions=questions
    )


# ==============================================================
# SECTION 8 - PROTECTED PDF DELIVERY
# ==============================================================

@app.route("/secure-pdf/<pdf_id>")
@login_required
def secure_pdf_view(pdf_id):

    pdfs = read_json("pdfs.json")

    pdf = next(
        (
            p for p in pdfs
            if p.get("id") == pdf_id
        ),
        None
    )

    if not pdf:
        abort(404)

    user = current_user()

    if pdf.get("is_paid"):

        purchases = read_json(
            "purchases.json"
        )

        owns_it = any(
            p.get("user_email") == user.get("email")
            and p.get("item_id") == pdf_id
            for p in purchases
        )

        if not owns_it:
            abort(403)

    for p in pdfs:

        if p.get("id") == pdf_id:

            p["downloads"] = (
                p.get("downloads", 0) + 1
            )

    write_json(
        "pdfs.json",
        pdfs
    )

    return send_from_directory(
        UPLOAD_PDF_DIR,
        pdf["file_name"]
    )


# ==============================================================
# SECTION 9 - PAYMENTS
# ==============================================================

@app.route(
    "/buy/<item_type>/<item_id>",
    methods=["POST"]
)
@login_required
def buy_item(item_type, item_id):

    if not PAYMENTS_ENABLED:

        flash(
            "Online payments are being set up. "
            "Please check back soon.",
            "info"
        )

        return redirect(
            request.referrer
            or url_for("home")
        )

    # ----------------------------------------------------------
    # FUTURE CASHFREE INTEGRATION
    # ----------------------------------------------------------
    #
    # Real payment gateway integration should create an order,
    # redirect the user to the gateway, and only add a purchase
    # after successful payment verification/webhook.
    #

    user = current_user()

    purchases = read_json(
        "purchases.json"
    )

    purchases.append({

        "user_email": user["email"],

        "item_type": item_type,

        "item_id": item_id,

        "date": datetime.now().strftime(
            "%Y-%m-%d"
        ),
    })

    write_json(
        "purchases.json",
        purchases
    )

    flash(
        "Purchase complete. "
        "You now have access to this item.",
        "success"
    )

    return redirect(
        request.referrer
        or url_for("home")
    )


# ==============================================================
# ERROR PAGES
# ==============================================================

@app.errorhandler(404)
def not_found(e):

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(403)
def forbidden(e):

    return render_template(
        "403.html"
    ), 403


# ==============================================================
# RUN APP
# ==============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)

    print(
        "  Chanakya Competition Cracker (CCC) is starting..."
    )

    print(
        f"  Open your browser to: http://localhost:{PORT}"
    )

    print(
        f"  Resend configured: {'YES' if RESEND_API_KEY else 'NO'}"
    )

    print(
        f"  Email From: {EMAIL_FROM}"
    )

    print("=" * 60 + "\n")

    app.run(
        debug=DEBUG_MODE,
        port=PORT,
        host="0.0.0.0"
    )
```
