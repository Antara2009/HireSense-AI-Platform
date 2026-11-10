import os
import sqlite3
import smtplib
from email.message import EmailMessage
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import init_db, get_db, seed_data, close_db
from resume_parser import extract_resume_text
from matcher import analyze_resume
from recommendations import recommend_courses

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
OFFER_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.teardown_appcontext(close_db)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()
seed_data()

def send_decision_email(recipient, subject, body):
    """Send email only when SMTP settings are explicitly configured."""
    host = os.environ.get("MAIL_SERVER")
    username = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")
    sender = os.environ.get("MAIL_DEFAULT_SENDER", username or "")
    if not all([host, username, password, sender, recipient]):
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    port = int(os.environ.get("MAIL_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)
    return True

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum upload size is 5 MB.", "danger")
    return redirect(url_for("student_dashboard"))

@app.route("/")
def index():
    db = get_db()
    job_count = db.execute("SELECT COUNT(*) FROM jobs WHERE is_active=1").fetchone()[0]
    if session.get("user_id"):
        return redirect(url_for("student_dashboard" if session.get("role") == "student" else "company_dashboard"))
    return render_template("index.html", job_count=job_count)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        if not name or not email or len(password) < 8 or role not in {"student", "company"}:
            flash("Enter all details. Password must contain at least 8 characters.", "danger")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                (name, email, generate_password_hash(password), role)
            )
            db.commit()
        except Exception:
            flash("This email is already registered. Please log in.", "warning")
            return render_template("register.html")
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("student_dashboard" if user["role"] == "student" else "company_dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/student")
@login_required("student")
def student_dashboard():
    jobs = get_db().execute("SELECT * FROM jobs WHERE is_active=1 ORDER BY created_at DESC LIMIT 6").fetchall()
    applications = get_db().execute("SELECT a.*, j.title, j.company, alt.title AS alternate_title FROM applications a JOIN jobs j ON j.id=a.job_id LEFT JOIN jobs alt ON alt.id=a.alternate_job_id WHERE a.student_id=? ORDER BY a.created_at DESC", (session["user_id"],)).fetchall()
    notifications = get_db().execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (session["user_id"],)).fetchall()
    return render_template("student_dashboard.html", jobs=jobs, applications=applications, notifications=notifications)

@app.route("/analyze", methods=["POST"])
@login_required("student")
def analyze():
    file = request.files.get("resume")
    target_role = request.form.get("target_role", "").strip()
    if not file or not file.filename:
        flash("Please choose a resume file.", "warning")
        return redirect(url_for("student_dashboard"))
    if not allowed_file(file.filename):
        flash("Supported formats: PDF, DOCX and TXT.", "danger")
        return redirect(url_for("student_dashboard"))

    safe_name = secure_filename(file.filename)
    unique_name = f"user{session['user_id']}_{safe_name}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(path)
    try:
        resume_text = extract_resume_text(path, safe_name.rsplit(".", 1)[1].lower())
    except Exception as exc:
        os.remove(path) if os.path.exists(path) else None
        flash(f"Could not read this file. Please try another PDF, DOCX or TXT file. ({exc})", "danger")
        return redirect(url_for("student_dashboard"))
    finally:
        # Remove the uploaded copy after extraction; only the analysis summary is retained.
        if os.path.exists(path):
            os.remove(path)
    if len(resume_text.strip()) < 30:
        flash("The file contains too little readable text. Try a text-based PDF or DOCX.", "warning")
        return redirect(url_for("student_dashboard"))

    db = get_db()
    role_row = db.execute("SELECT * FROM jobs WHERE title=? AND is_active=1 ORDER BY id LIMIT 1", (target_role,)).fetchone() if target_role else None
    if role_row:
        job_title = role_row["title"]
        required = role_row["skills"]
        description = role_row["description"]
    else:
        job_title = target_role or "General Technology Role"
        required = request.form.get("custom_skills", "").strip()
        description = ""
        if not required:
            required = "python, communication, problem solving, sql, teamwork"

    result = analyze_resume(resume_text, required, description)
    courses = recommend_courses(result["missing_skills"])
    db.execute(
        "INSERT INTO analyses(user_id,filename,target_role,score,matched_skills,missing_skills,resume_text) VALUES(?,?,?,?,?,?,?)",
        (session["user_id"], safe_name, job_title, result["score"],
         ", ".join(result["matched_skills"]), ", ".join(result["missing_skills"]), None)
    )
    db.commit()

    # Recommend roles based on the extracted resume skills, not demographic attributes.
    all_jobs = db.execute("SELECT * FROM jobs WHERE is_active=1").fetchall()
    job_matches = []
    for job in all_jobs:
        jr = analyze_resume(resume_text, job["skills"], job["description"])
        if jr["score"] > 0:
            job_matches.append({"job": job, "score": jr["score"], "matched": jr["matched_skills"]})
    job_matches.sort(key=lambda item: item["score"], reverse=True)

    return render_template("results.html", result=result, courses=courses, job_title=job_title,
                           filename=safe_name, job_matches=job_matches[:5])

@app.route("/company")
@login_required("company")
def company_dashboard():
    db = get_db()
    jobs = db.execute("""SELECT j.*, COUNT(a.id) AS application_count,
        SUM(CASE WHEN a.status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted_count
        FROM jobs j LEFT JOIN applications a ON a.job_id=j.id
        WHERE j.company_id=? GROUP BY j.id ORDER BY j.created_at DESC""", (session["user_id"],)).fetchall()
    totals = db.execute("""SELECT COUNT(a.id) total,
        SUM(CASE WHEN a.status='Applied' THEN 1 ELSE 0 END) pending,
        SUM(CASE WHEN a.status='Shortlisted' THEN 1 ELSE 0 END) shortlisted
        FROM applications a JOIN jobs j ON j.id=a.job_id WHERE j.company_id=?""", (session["user_id"],)).fetchone()
    return render_template("company_dashboard.html", jobs=jobs, totals=totals)

@app.route("/apply/<int:job_id>", methods=["POST"])
@login_required("student")
def apply_job(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=? AND is_active=1", (job_id,)).fetchone()
    if not job:
        abort(404)
    file = request.files.get("resume")
    if not file or not file.filename or not allowed_file(file.filename):
        flash("Upload a PDF, DOCX or TXT resume to apply.", "warning")
        return redirect(url_for("jobs"))
    filename = secure_filename(file.filename)
    stored_name = f"application_{session['user_id']}_{job_id}_{filename}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    file.save(path)
    try:
        text = extract_resume_text(path, filename.rsplit('.', 1)[1].lower())
        if len(text.strip()) < 30:
            raise ValueError("The resume contains too little readable text.")
        result = analyze_resume(text, job["skills"], job["description"])
        db.execute("""INSERT INTO applications(job_id,student_id,resume_filename,resume_path,resume_text,score,matched_skills,missing_skills)
            VALUES(?,?,?,?,?,?,?,?)""", (job_id, session["user_id"], filename, stored_name, text,
            result["score"], ", ".join(result["matched_skills"]), ", ".join(result["missing_skills"])))
        db.commit()
    except sqlite3.IntegrityError:
        if os.path.exists(path): os.remove(path)
        flash("You have already applied for this vacancy.", "warning")
        return redirect(url_for("jobs"))
    except Exception as exc:
        if os.path.exists(path): os.remove(path)
        flash(f"Could not submit application: {exc}", "danger")
        return redirect(url_for("jobs"))
    flash("Application submitted successfully. Your match insights are ready.", "success")
    return redirect(url_for("student_dashboard"))

@app.route("/company/screening/<int:job_id>")
@login_required("company")
def smart_screening(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=? AND company_id=?", (job_id, session["user_id"])).fetchone()
    if not job: abort(404)
    applicants = db.execute("""SELECT a.*, u.name, u.email FROM applications a
        JOIN users u ON u.id=a.student_id WHERE a.job_id=?
        ORDER BY a.score DESC, a.created_at ASC""", (job_id,)).fetchall()
    alternate_jobs = db.execute("SELECT id,title FROM jobs WHERE company_id=? AND is_active=1 AND id<>? ORDER BY title", (session["user_id"], job_id)).fetchall()
    return render_template("screening.html", job=job, applicants=applicants, alternate_jobs=alternate_jobs)

@app.route("/company/application/<int:application_id>/status", methods=["POST"])
@login_required("company")
def update_application_status(application_id):
    status = request.form.get("status")
    allowed_statuses = {"Applied", "Under Review", "Shortlisted", "Selected", "Rejected", "Alternate Position"}
    if status not in allowed_statuses:
        abort(400)
    db = get_db()
    row = db.execute("""SELECT a.id, a.student_id, a.job_id, u.name, u.email, j.title
        FROM applications a JOIN jobs j ON j.id=a.job_id
        JOIN users u ON u.id=a.student_id
        WHERE a.id=? AND j.company_id=?""", (application_id, session["user_id"])).fetchone()
    if not row:
        abort(404)

    note = request.form.get("decision_note", "").strip()[:1000]
    alternate_job_id = None
    if status == "Alternate Position":
        try:
            alternate_job_id = int(request.form.get("alternate_job_id", ""))
        except (TypeError, ValueError):
            flash("Choose an alternate vacancy before saving this decision.", "warning")
            return redirect(url_for("smart_screening", job_id=row["job_id"]))
        alternate = db.execute("SELECT id FROM jobs WHERE id=? AND company_id=? AND is_active=1", (alternate_job_id, session["user_id"])).fetchone()
        if not alternate or alternate_job_id == row["job_id"]:
            flash("Choose another active vacancy posted by your company.", "warning")
            return redirect(url_for("smart_screening", job_id=row["job_id"]))

    offer_path = None
    offer = request.files.get("offer_letter")
    if status == "Selected":
        if offer and offer.filename:
            if not offer.filename.lower().endswith(".pdf"):
                flash("Offer letter must be a PDF file.", "danger")
                return redirect(url_for("smart_screening", job_id=row["job_id"]))
            safe_offer = secure_filename(offer.filename)
            offer_path = f"offer_{application_id}_{safe_offer}"
            offer.save(os.path.join(app.config["UPLOAD_FOLDER"], offer_path))

    db.execute("UPDATE applications SET status=?, decision_note=?, offer_letter_path=COALESCE(?, offer_letter_path), alternate_job_id=? WHERE id=?",
               (status, note, offer_path, alternate_job_id, application_id))

    messages = {
        "Applied": ("Application update", "Your application status is now Applied."),
        "Under Review": ("Application under review", "The company is reviewing your application."),
        "Shortlisted": ("You have been shortlisted", "The recruiter has shortlisted your application."),
        "Selected": ("Congratulations — selected", "The company marked you as selected. Check your application for the offer letter."),
        "Rejected": ("Application update", "The company has decided not to proceed with this application."),
        "Alternate Position": ("Another opportunity may fit", "The recruiter has suggested another vacancy at the same company.")
    }
    title, message = messages[status]
    if note:
        message += " Recruiter note: " + note
    if alternate_job_id:
        alt_title = db.execute("SELECT title FROM jobs WHERE id=?", (alternate_job_id,)).fetchone()["title"]
        message += " Suggested role: " + alt_title + "."
    db.execute("INSERT INTO notifications(user_id,application_id,title,message) VALUES(?,?,?,?)",
               (row["student_id"], application_id, title, message))
    db.commit()
    email_sent = False
    try:
        email_sent = send_decision_email(row["email"], title, message)
    except Exception:
        app.logger.exception("Decision email could not be sent")
    if email_sent:
        flash("Candidate decision saved. In-app notification and email sent.", "success")
    else:
        flash("Candidate decision saved and in-app notification created. Configure SMTP to enable email delivery.", "success")
    return redirect(url_for("smart_screening", job_id=row["job_id"]))

@app.route("/student/offer/<int:application_id>")
@login_required("student")
def download_offer_letter(application_id):
    row = get_db().execute("SELECT offer_letter_path FROM applications WHERE id=? AND student_id=?",
                           (application_id, session["user_id"])).fetchone()
    if not row or not row["offer_letter_path"]:
        abort(404)
    path = os.path.join(app.config["UPLOAD_FOLDER"], row["offer_letter_path"])
    if not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name="HireSense_Offer_Letter.pdf")

@app.route("/company/screening/<int:job_id>/bulk-shortlist", methods=["POST"])
@login_required("company")
def bulk_shortlist(job_id):
    db = get_db()
    job = db.execute("SELECT id FROM jobs WHERE id=? AND company_id=?", (job_id, session["user_id"])).fetchone()
    if not job: abort(404)
    ids = request.form.getlist("application_ids")
    if ids:
        placeholders = ",".join("?" for _ in ids)
        db.execute(f"UPDATE applications SET status='Shortlisted' WHERE job_id=? AND id IN ({placeholders})", [job_id] + ids)
        db.commit()
        flash(f"{len(ids)} candidate(s) shortlisted.", "success")
    else:
        flash("Select at least one candidate first.", "warning")
    return redirect(url_for("smart_screening", job_id=job_id))

@app.route("/company/resume/<int:application_id>")
@login_required("company")
def download_application_resume(application_id):
    row = get_db().execute("""SELECT a.resume_path,a.resume_filename FROM applications a
        JOIN jobs j ON j.id=a.job_id WHERE a.id=? AND j.company_id=?""", (application_id, session["user_id"])).fetchone()
    if not row: abort(404)
    path = os.path.join(app.config["UPLOAD_FOLDER"], row["resume_path"])
    if not os.path.isfile(path): abort(404)
    return send_file(path, as_attachment=True, download_name=row["resume_filename"])

@app.route("/jobs/create", methods=["POST"])
@login_required("company")
def create_job():
    title = request.form.get("title", "").strip()
    department = request.form.get("department", "").strip()
    location = request.form.get("location", "").strip()
    skills = request.form.get("skills", "").strip()
    description = request.form.get("description", "").strip()
    if not all([title, department, location, skills, description]):
        flash("Please complete all vacancy fields.", "warning")
        return redirect(url_for("company_dashboard"))
    db = get_db()
    db.execute("INSERT INTO jobs(title,company,department,location,skills,description,company_id) VALUES(?,?,?,?,?,?,?)",
               (title, session["name"], department, location, skills, description, session["user_id"]))
    db.commit()
    flash("Vacancy published successfully.", "success")
    return redirect(url_for("company_dashboard"))

@app.route("/notifications/read", methods=["POST"])
@login_required("student")
def mark_notifications_read():
    get_db().execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    get_db().commit()
    return redirect(url_for("student_dashboard"))

@app.route("/jobs")
def jobs():
    rows = get_db().execute("SELECT * FROM jobs WHERE is_active=1 ORDER BY created_at DESC").fetchall()
    applied_ids = []
    if session.get("role") == "student":
        applied_ids = [r[0] for r in get_db().execute("SELECT job_id FROM applications WHERE student_id=?", (session["user_id"],)).fetchall()]
    return render_template("jobs.html", jobs=rows, applied_ids=applied_ids)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)
