"""Flask API and local web server for the Student Placement System."""

from functools import wraps
import json
import os
from pathlib import Path
import secrets
from datetime import date

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash

from database import (
    DATABASE_PATH,
    application_dict,
    company_dict,
    connect,
    init_db,
    job_dict,
    student_dict,
)
from eligibility import check_eligibility
from test_criteria import test_criteria

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "Front end"
SECRET_PATH = PROJECT_ROOT / ".flask_secret"


def get_secret_key():
    configured = os.environ.get("FLASK_SECRET_KEY")
    if configured:
        return configured
    if not SECRET_PATH.exists():
        SECRET_PATH.write_text(secrets.token_hex(32), encoding="utf-8")
    return SECRET_PATH.read_text(encoding="utf-8").strip()


app = Flask(__name__, static_folder=str(FRONTEND_ROOT), static_url_path="")
app.config.update(SECRET_KEY=get_secret_key(), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
init_db()


def login_required(role=None):
    def decorate(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return jsonify({"error": "Please sign in to continue."}), 401
            if role and session.get("role") != role:
                return jsonify({"error": "You do not have permission to do that."}), 403
            # A signed cookie can outlive a deleted or incomplete database account.
            # Validate it before handlers index user/student rows.
            with connect() as connection:
                user = connection.execute(
                    "SELECT id, role FROM users WHERE id = ?", (user_id,)
                ).fetchone()
                if not user or user["role"] != session.get("role"):
                    session.clear()
                    return jsonify({"error": "Your session expired. Please sign in again."}), 401
                if user["role"] == "student":
                    student_row = connection.execute(
                        "SELECT id FROM students WHERE id = ?", (user_id,)
                    ).fetchone()
                    if not student_row:
                        session.clear()
                        return jsonify({"error": "Your student profile is missing. Please register again."}), 401
            return handler(*args, **kwargs)

        return wrapped

    return decorate


def current_student(connection):
    if session.get("role") != "student":
        return None
    row = connection.execute(
        """SELECT s.*, u.email FROM students s JOIN users u ON u.id = s.id WHERE s.id = ?""",
        (session["user_id"],),
    ).fetchone()
    return student_dict(row)


def current_session_payload(connection):
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = connection.execute("SELECT id, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        session.clear()
        return None
    result = {"userId": user["id"], "email": user["email"], "role": user["role"]}
    if user["role"] == "student":
        result["studentId"] = user["id"]
    return result


def all_students(connection):
    rows = connection.execute(
        """SELECT s.*, u.email FROM students s JOIN users u ON u.id = s.id ORDER BY s.name"""
    ).fetchall()
    return [student_dict(row) for row in rows]


def all_companies(connection):
    return [company_dict(row) for row in connection.execute("SELECT * FROM companies ORDER BY name")]


def all_jobs(connection):
    return [job_dict(row) for row in connection.execute("SELECT * FROM jobs ORDER BY id DESC")]


def all_applications(connection, student_id=None):
    if student_id is None:
        rows = connection.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM applications WHERE student_id = ? ORDER BY id DESC", (student_id,)
        ).fetchall()
    return [application_dict(row) for row in rows]


def eligible_for(student, job):
    if not isinstance(student, dict) or not isinstance(job, dict):
        return "Criteria Not Available"
    if not student.get("branch"):
        return "Criteria Not Available"
    criteria_type = job.get("criteriaType")
    minimum_criteria = job.get("minimumCriteria")
    if criteria_type not in ("percentage", "cgpa") or minimum_criteria is None:
        return "Criteria Not Available"
    drive = {"criteria_type": criteria_type, "minimum_criteria": minimum_criteria}
    academic_result = check_eligibility(student, drive)
    if academic_result != "Eligible":
        return academic_result
    branches = job.get("branches") or []
    student_branch = str(student.get("branch") or "").strip()
    if not student_branch:
        return "Criteria Not Available"
    if "Any branch" not in branches and not any(
        str(branch).lower() in student_branch.lower() or student_branch.lower() in str(branch).lower()
        for branch in branches
    ):
        return "Not Eligible"
    return "Eligible"


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/bootstrap")
def bootstrap():
    with connect() as connection:
        signed_in = current_session_payload(connection)
        if signed_in and signed_in["role"] == "admin":
            people = all_students(connection)
            applications = all_applications(connection)
        elif signed_in and signed_in["role"] == "student":
            person = current_student(connection)
            people = [person] if person else []
            applications = all_applications(connection, signed_in["studentId"])
        else:
            people, applications = [], []

        notifications = []
        saved_ids = []
        if signed_in:
            notifications = [dict(row) for row in connection.execute(
                "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (signed_in["userId"],)
            )]
            for item in notifications:
                item["unread"] = bool(item["unread"])
            saved_ids = [row[0] for row in connection.execute(
                "SELECT job_id FROM saved_jobs WHERE user_id = ?", (signed_in["userId"],)
            )]

        return jsonify(
            {
                "session": signed_in,
                "students": people,
                "companies": all_companies(connection),
                "jobs": all_jobs(connection),
                "applications": applications,
                "notifications": notifications,
                "savedJobIds": saved_ids,
            }
        )


@app.get("/api/auth/session")
def auth_session():
    with connect() as connection:
        return jsonify(current_session_payload(connection))


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    branch = str(data.get("branch", "")).strip()
    year = str(data.get("year", "")).strip()
    if not name or not email or not branch or not year or len(password) < 6:
        return jsonify({"error": "Fill in all required fields and use a password with at least 6 characters."}), 400

    from werkzeug.security import generate_password_hash

    try:
        with connect() as connection:
            cursor = connection.execute(
                "INSERT INTO users(email, password_hash, role) VALUES (?, ?, 'student')",
                (email, generate_password_hash(password)),
            )
            user_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO students(id, name, branch, year) VALUES (?, ?, ?, ?)",
                (user_id, name, branch, year),
            )
        session.clear()
        session.update(user_id=user_id, role="student")
        return jsonify({"session": {"userId": user_id, "studentId": user_id, "role": "student", "email": email}}), 201
    except Exception as error:
        if "UNIQUE constraint failed: users.email" in str(error):
            return jsonify({"error": "An account with this email already exists. Please sign in."}), 409
        raise


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", "student"))
    if role not in ("student", "admin"):
        return jsonify({"error": "Invalid account type."}), 400
    with connect() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or user["role"] != role or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Email or password is incorrect."}), 401
    session.clear()
    session.update(user_id=user["id"], role=user["role"])
    payload = {"userId": user["id"], "role": user["role"], "email": user["email"]}
    if user["role"] == "student":
        payload["studentId"] = user["id"]
    return jsonify({"session": payload})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.put("/api/profile")
@login_required("student")
def update_profile():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    branch = str(data.get("branch", "")).strip()
    year = str(data.get("year", "")).strip()
    if not name or not email or not branch or not year:
        return jsonify({"error": "Name, email, branch, and graduation year are required."}), 400
    try:
        with connect() as connection:
            connection.execute("UPDATE users SET email = ? WHERE id = ?", (email, session["user_id"]))
            connection.execute(
                """UPDATE students SET name=?, branch=?, year=?, phone=?, cgpa=?, percentage=?,
                   backlogs=?, skills_json=?, bio=?, resume=? WHERE id=?""",
                (
                    name, branch, year, str(data.get("phone", "")).strip(),
                    float(data.get("cgpa") or 0), float(data.get("percentage") or 0),
                    int(data.get("backlogs") or 0), json.dumps(data.get("skills") or []),
                    str(data.get("bio", "")).strip(), str(data.get("resume", "")).strip(), session["user_id"],
                ),
            )
    except Exception as error:
        if "UNIQUE constraint failed: users.email" in str(error):
            return jsonify({"error": "That email is already in use."}), 409
        raise
    with connect() as connection:
        updated_student = current_student(connection)
    return jsonify({"student": updated_student})


@app.get("/api/eligibility/<int:student_id>/<int:job_id>")
@login_required()
def eligibility(student_id, job_id):
    if session["role"] == "student" and session["user_id"] != student_id:
        return jsonify({"error": "You can only check your own eligibility."}), 403
    with connect() as connection:
        person_row = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        job_row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not person_row or not job_row:
            return jsonify({"error": "Student or job not found."}), 404
        person = student_dict(person_row)
        job = job_dict(job_row)
        if not isinstance(person, dict) or not isinstance(job, dict):
            return jsonify({"error": "Student or job information could not be loaded."}), 404

        company_id = job.get("companyId")
        if company_id is None:
            return jsonify({"error": "The company for this job could not be found."}), 404
        company_row = connection.execute("SELECT name FROM companies WHERE id = ?", (company_id,)).fetchone()
        if company_row is None:
            return jsonify({"error": "The company for this job could not be found."}), 404
        company_name = company_row["name"] if isinstance(company_row, dict) else None
        if not company_name:
            return jsonify({"error": "The company for this job could not be found."}), 404

        result = eligible_for(person, job)
        minimum_criteria = job.get("minimumCriteria")
        criteria_type = job.get("criteriaType")
        criteria_message = test_criteria.get(
            company_name,
            (
                f"Minimum {minimum_criteria} {criteria_type} "
                if minimum_criteria is not None and criteria_type
                else "Minimum criteria not available"
            ),
        )

    return jsonify({
        "student": person["name"],
        "company": company_name,
        "role": job["title"],
        "result": result,
        "criteria": criteria_message,
    })


@app.post("/api/applications")
@login_required("student")
def create_application():
    data = request.get_json(silent=True) or {}
    job_id = int(data.get("jobId") or 0)
    with connect() as connection:
        person_row = connection.execute("SELECT * FROM students WHERE id = ?", (session["user_id"],)).fetchone()
        job_row = connection.execute("SELECT * FROM jobs WHERE id = ? AND status = 'Open'", (job_id,)).fetchone()
        if not person_row or not job_row:
            return jsonify({"error": "This job is no longer available."}), 404
        person = student_dict(person_row)
        job = job_dict(job_row)
        if not isinstance(person, dict) or not isinstance(job, dict):
            return jsonify({"error": "This job is no longer available."}), 404
        result = eligible_for(person, job)
        if result != "Eligible":
            return jsonify({"error": "You do not meet this job's eligibility criteria."}), 403
        try:
            cursor = connection.execute(
                "INSERT INTO applications(student_id, job_id, applied_at) VALUES (?, ?, ?)",
                (session["user_id"], job_id, date.today().isoformat()),
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                return jsonify({"error": "You have already applied to this job."}), 409
            raise
        application = connection.execute("SELECT * FROM applications WHERE id = ?", (cursor.lastrowid,)).fetchone()
        job_title = job.get("title") or "this role"
        connection.execute(
            "INSERT INTO notifications(user_id, title, body, kind) VALUES (?, ?, ?, 'success')",
            (session["user_id"], "Application submitted", f"Your application for {job_title} was received."),
        )
        return jsonify({"application": application_dict(application)}), 201


@app.patch("/api/applications/<int:application_id>")
@login_required("admin")
def update_application(application_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", ""))
    allowed = {"Applied", "Under review", "Shortlisted", "Interview", "Selected", "Rejected"}
    if status not in allowed:
        return jsonify({"error": "Invalid application status."}), 400
    with connect() as connection:
        row = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if not row:
            return jsonify({"error": "Application not found."}), 404
        note = f"Status updated by placement cell: {status}."
        connection.execute("UPDATE applications SET status=?, note=? WHERE id=?", (status, note, application_id))
        connection.execute(
            "INSERT INTO notifications(user_id, title, body, kind) VALUES (?, ?, ?, 'info')",
            (row["student_id"], "Application status updated", note),
        )
        updated = connection.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return jsonify({"application": application_dict(updated)})


@app.post("/api/companies")
@login_required("admin")
def create_company():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "Company name is required."}), 400
    with connect() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO companies(name, industry, location, about, logo) VALUES (?, ?, ?, ?, ?)",
                (name, str(data.get("industry", "")).strip(), str(data.get("location", "")).strip(),
                 str(data.get("about", "")).strip(), name[:1].upper()),
            )
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                return jsonify({"error": "This company already exists."}), 409
            raise
        return jsonify({"company": company_dict(connection.execute("SELECT * FROM companies WHERE id=?", (cursor.lastrowid,)).fetchone())}), 201


@app.post("/api/jobs")
@login_required("admin")
def create_job():
    data = request.get_json(silent=True) or {}
    required = ("title", "companyId", "type", "location", "deadline")
    if any(not data.get(key) for key in required):
        return jsonify({"error": "Title, company, type, location, and deadline are required."}), 400
    try:
        company_id = int(data["companyId"])
        min_cgpa = float(data.get("minCgpa") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid company or CGPA value."}), 400
    with connect() as connection:
        if not connection.execute("SELECT id FROM companies WHERE id=?", (company_id,)).fetchone():
            return jsonify({"error": "Company not found."}), 404
        cursor = connection.execute(
            """INSERT INTO jobs(title,company_id,type,location,salary,min_cgpa,min_percentage,criteria_type,
               minimum_criteria,branches_json,skills_json,posted,deadline,description,responsibilities_json,status)
               VALUES(?,?,?,?,?,?,0,'cgpa',?,?,?,?,?,?,?,'Open')""",
            (str(data["title"]).strip(), company_id, str(data["type"]), str(data["location"]).strip(),
             str(data.get("salary", "")).strip(), min_cgpa, min_cgpa,
             json.dumps(data.get("branches") or ["Any branch"]), json.dumps(data.get("skills") or []),
             "Today", str(data["deadline"]), str(data.get("description", "")).strip(),
             json.dumps(data.get("responsibilities") or [])),
        )
        row = connection.execute("SELECT * FROM jobs WHERE id=?", (cursor.lastrowid,)).fetchone()
        return jsonify({"job": job_dict(row)}), 201


@app.patch("/api/notifications/read")
@login_required()
def mark_notifications_read():
    with connect() as connection:
        connection.execute("UPDATE notifications SET unread=0 WHERE user_id=?", (session["user_id"],))
    return jsonify({"ok": True})


@app.delete("/api/notifications/<int:notification_id>")
@login_required()
def delete_notification(notification_id):
    with connect() as connection:
        connection.execute("DELETE FROM notifications WHERE id=? AND user_id=?", (notification_id, session["user_id"]))
    return jsonify({"ok": True})


@app.put("/api/saved-jobs/<int:job_id>")
@login_required()
def toggle_saved_job(job_id):
    with connect() as connection:
        if not connection.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone():
            return jsonify({"error": "Job not found."}), 404
        saved = connection.execute("SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?", (session["user_id"], job_id)).fetchone()
        if saved:
            connection.execute("DELETE FROM saved_jobs WHERE user_id=? AND job_id=?", (session["user_id"], job_id))
            return jsonify({"saved": False})
        connection.execute("INSERT INTO saved_jobs(user_id,job_id) VALUES(?,?)", (session["user_id"], job_id))
        return jsonify({"saved": True})


@app.get("/")
def index():
    return send_from_directory(FRONTEND_ROOT, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
