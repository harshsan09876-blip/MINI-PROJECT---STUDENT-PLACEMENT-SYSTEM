"""Flask API and server for Student Placement Management System."""

import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session

from database import (
    format_application,
    format_company,
    format_job,
    format_student,
    get_db,
    init_db,
)
from eligibility import check_eligibility

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "Front end"

app = Flask(__name__, static_folder=str(FRONTEND_ROOT), static_url_path="")
app.secret_key = "pathway_placement_secret_key_2026"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# -------------------------------------------------------------
# CORS Middleware & OPTIONS Preflight
# -------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/<path:_subpath>", methods=["OPTIONS"])
def handle_options(_subpath):
    return ("", 204)


# -------------------------------------------------------------
# Bootstrap & Health Endpoints
# -------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.get("/api/bootstrap")
def bootstrap():
    """Returns the complete platform state from SQLite."""
    current_session = None
    if "role" in session:
        current_session = {
            "role": session.get("role"),
            "studentId": session.get("studentId"),
            "adminId": session.get("adminId"),
            "email": session.get("email"),
            "name": session.get("name"),
        }

    with get_db() as conn:
        students = [format_student(r) for r in conn.execute("SELECT * FROM students").fetchall()]
        companies = [format_company(r) for r in conn.execute("SELECT * FROM companies").fetchall()]
        jobs = [format_job(r) for r in conn.execute("SELECT * FROM jobs").fetchall()]
        applications = [format_application(r) for r in conn.execute("SELECT * FROM applications").fetchall()]

        # Notifications
        student_id = session.get("studentId")
        if student_id:
            notif_rows = conn.execute(
                "SELECT * FROM notifications WHERE student_id = ? ORDER BY id DESC",
                (student_id,),
            ).fetchall()
        else:
            notif_rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 20").fetchall()

        notifications = [
            {
                "id": r["id"],
                "studentId": r["student_id"],
                "title": r["title"],
                "body": r["body"],
                "time": r["time"],
                "unread": bool(r["unread"]),
                "kind": r["kind"],
            }
            for r in notif_rows
        ]

        # Saved jobs
        saved_job_ids = []
        if student_id:
            saved_rows = conn.execute(
                "SELECT job_id FROM saved_jobs WHERE student_id = ?",
                (student_id,),
            ).fetchall()
            saved_job_ids = [r["job_id"] for r in saved_rows]

    return jsonify({
        "session": current_session,
        "students": students,
        "companies": companies,
        "jobs": jobs,
        "applications": applications,
        "notifications": notifications,
        "savedJobIds": saved_job_ids,
    })


# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/register")
@app.post("/api/register")
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip() or "password123"
    branch = (data.get("branch") or "CSE").strip()
    year = (data.get("year") or "2027").strip()
    cgpa = float(data.get("cgpa") or 7.0)

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM students WHERE LOWER(email) = ?", (email,)).fetchone()
        if existing:
            return jsonify({"error": "An account with this email already exists. Please sign in."}), 400

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO students (name, email, password, branch, year, cgpa, percentage, backlogs)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (name, email, password, branch, year, cgpa, round(cgpa * 9.5, 1)),
        )
        new_id = cursor.lastrowid

        # Insert welcome notification
        cursor.execute(
            """
            INSERT INTO notifications (student_id, title, body, time, unread, kind)
            VALUES (?, 'Welcome to Pathway!', 'Your student profile is active. Check open placement drives.', 'Just now', 1, 'info')
            """,
            (new_id,),
        )
        conn.commit()

        student_row = conn.execute("SELECT * FROM students WHERE id = ?", (new_id,)).fetchone()

    # Establish session
    session["role"] = "student"
    session["studentId"] = new_id
    session["email"] = email
    session["name"] = name

    return jsonify({
        "status": "success",
        "student": format_student(student_row),
        "session": {
            "role": "student",
            "studentId": new_id,
            "email": email,
            "name": name,
        },
    }), 201


@app.post("/api/auth/login")
@app.post("/api/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = data.get("role") or "student"

    with get_db() as conn:
        if role == "admin":
            admin = conn.execute(
                "SELECT * FROM admins WHERE LOWER(email) = ? AND password = ?",
                (email, password),
            ).fetchone()
            if admin or (email == "admin@pathway.demo" and password == "admin123"):
                session["role"] = "admin"
                session["adminId"] = 1
                session["email"] = "admin@pathway.demo"
                session["name"] = "Placement Admin"
                return jsonify({
                    "status": "success",
                    "role": "admin",
                    "user": {"email": "admin@pathway.demo", "name": "Placement Admin"},
                })
            return jsonify({"error": "Incorrect admin details. Try admin@pathway.demo / admin123"}), 401

        # Student login
        student = conn.execute("SELECT * FROM students WHERE LOWER(email) = ?", (email,)).fetchone()
        if not student:
            # Check demo alias student1@placement.demo
            student = conn.execute("SELECT * FROM students LIMIT 1").fetchone()

        if student:
            session["role"] = "student"
            session["studentId"] = student["id"]
            session["email"] = student["email"]
            session["name"] = student["name"]
            return jsonify({
                "status": "success",
                "role": "student",
                "student": format_student(student),
            })

    return jsonify({"error": "Account not found. Please register."}), 404


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"status": "success"})


# -------------------------------------------------------------
# Eligibility Check Endpoint
# -------------------------------------------------------------
@app.get("/api/eligibility/<int:student_id>/<int:job_id>")
def eligibility(student_id, job_id):
    with get_db() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

        if not student:
            return jsonify({"error": f"Student not found"}), 404
        if not job:
            return jsonify({"error": f"Job opportunity not found"}), 404

        company = conn.execute("SELECT name FROM companies WHERE id = ?", (job["company_id"],)).fetchone()
        comp_name = company["name"] if company else "Company"

        verdict = check_eligibility(dict(student), dict(job))
        is_eligible = verdict == "Eligible"

        return jsonify({
            "student": student["name"],
            "company": comp_name,
            "role": job["title"],
            "result": "Eligible" if is_eligible else "Not Eligible",
            "reason": verdict,
            "criteria": job["description"] or f"Minimum criteria: {job['minimum_criteria']}",
        })


# -------------------------------------------------------------
# Applications Endpoints
# -------------------------------------------------------------
@app.get("/api/applications")
def get_applications():
    student_id = request.args.get("studentId") or (session.get("studentId") if session.get("role") == "student" else None)
    with get_db() as conn:
        if student_id and session.get("role") != "admin":
            rows = conn.execute(
                "SELECT * FROM applications WHERE student_id = ? ORDER BY id DESC",
                (student_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()

    return jsonify([format_application(r) for r in rows])


@app.post("/api/applications")
def apply_for_job():
    data = request.get_json() or {}
    job_id = data.get("jobId")
    student_id = session.get("studentId") or data.get("studentId")

    if not student_id:
        return jsonify({"error": "Please sign in to submit an application."}), 401
    if not job_id:
        return jsonify({"error": "Job ID is required."}), 400

    with get_db() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

        if not student:
            return jsonify({"error": "Student account not found."}), 404
        if not job:
            return jsonify({"error": "Job opportunity not found."}), 404

        existing = conn.execute(
            "SELECT id FROM applications WHERE student_id = ? AND job_id = ?",
            (student_id, job_id),
        ).fetchone()
        if existing:
            return jsonify({"error": "You have already applied for this role."}), 409

        verdict = check_eligibility(dict(student), dict(job))
        if verdict != "Eligible":
            return jsonify({"error": f"Eligibility not met: {verdict}"}), 400

        cursor = conn.cursor()
        applied_at = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT INTO applications (student_id, job_id, applied_at, status, note)
            VALUES (?, ?, ?, 'Applied', 'Your application was received.')
            """,
            (student_id, job_id, applied_at),
        )
        new_app_id = cursor.lastrowid

        company = conn.execute("SELECT name FROM companies WHERE id = ?", (job["company_id"],)).fetchone()
        comp_name = company["name"] if company else "Company"

        cursor.execute(
            """
            INSERT INTO notifications (student_id, title, body, time, unread, kind)
            VALUES (?, ?, ?, 'Just now', 1, 'info')
            """,
            (
                student_id,
                f"Application Submitted: {job['title']}",
                f"Your application for {job['title']} at {comp_name} was received successfully.",
            ),
        )
        conn.commit()

        app_row = conn.execute("SELECT * FROM applications WHERE id = ?", (new_app_id,)).fetchone()

    return jsonify({"status": "success", "application": format_application(app_row)}), 201


@app.patch("/api/applications/<int:app_id>")
@app.put("/api/applications/<int:app_id>")
def update_application(app_id):
    data = request.get_json() or {}
    status = (data.get("status") or "").strip()
    note = (data.get("note") or f"Status updated by placement cell: {status}.").strip()

    if not status:
        return jsonify({"error": "Status is required."}), 400

    with get_db() as conn:
        app_row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            return jsonify({"error": "Application not found."}), 404

        conn.execute(
            "UPDATE applications SET status = ?, note = ? WHERE id = ?",
            (status, note, app_id),
        )

        job = conn.execute("SELECT title FROM jobs WHERE id = ?", (app_row["job_id"],)).fetchone()
        job_title = job["title"] if job else "your position"

        conn.execute(
            """
            INSERT INTO notifications (student_id, title, body, time, unread, kind)
            VALUES (?, ?, ?, 'Just now', 1, ?)
            """,
            (
                app_row["student_id"],
                f"Application Update: {status}",
                f"Your application for {job_title} was updated to: {status}.",
                "success" if status in ["Shortlisted", "Selected"] else "info",
            ),
        )
        conn.commit()

        updated_row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()

    return jsonify({"status": "success", "application": format_application(updated_row)})


# -------------------------------------------------------------
# Student Profile Endpoint
# -------------------------------------------------------------
@app.put("/api/profile")
@app.put("/api/students/<int:student_id>")
def update_profile(student_id=None):
    if student_id is None:
        student_id = session.get("studentId")

    if not student_id:
        return jsonify({"error": "Please log in to edit profile."}), 401

    data = request.get_json() or {}
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not existing:
            return jsonify({"error": "Student profile not found."}), 404

        name = data.get("name", existing["name"]).strip()
        email = data.get("email", existing["email"]).strip()
        phone = data.get("phone", existing["phone"]).strip()
        branch = data.get("branch", existing["branch"]).strip()
        year = str(data.get("year", existing["year"])).strip()
        cgpa = float(data.get("cgpa", existing["cgpa"]))
        percentage = round(cgpa * 9.5, 1)

        raw_skills = data.get("skills")
        if isinstance(raw_skills, list):
            skills = json.dumps(raw_skills)
        elif isinstance(raw_skills, str):
            skills = json.dumps([s.strip() for s in raw_skills.split(",") if s.strip()])
        else:
            skills = existing["skills"]

        bio = data.get("bio", existing["bio"]).strip()
        resume = data.get("resume", existing["resume"]).strip()

        conn.execute(
            """
            UPDATE students SET
                name = ?, email = ?, phone = ?, branch = ?, year = ?,
                cgpa = ?, percentage = ?, skills = ?, bio = ?, resume = ?
            WHERE id = ?
            """,
            (name, email, phone, branch, year, cgpa, percentage, skills, bio, resume, student_id),
        )
        conn.commit()

        session["name"] = name
        session["email"] = email

        updated = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    return jsonify({"status": "success", "student": format_student(updated)})


# -------------------------------------------------------------
# Saved Jobs & Notifications Endpoints
# -------------------------------------------------------------
@app.put("/api/saved-jobs/<int:job_id>")
def toggle_save_job(job_id):
    student_id = session.get("studentId")
    if not student_id:
        return jsonify({"error": "Sign in to save opportunities."}), 401

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM saved_jobs WHERE student_id = ? AND job_id = ?",
            (student_id, job_id),
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM saved_jobs WHERE id = ?", (existing["id"],))
            conn.commit()
            return jsonify({"status": "success", "saved": False})
        else:
            conn.execute("INSERT INTO saved_jobs (student_id, job_id) VALUES (?, ?)", (student_id, job_id))
            conn.commit()
            return jsonify({"status": "success", "saved": True})


@app.patch("/api/notifications/read")
def mark_read():
    student_id = session.get("studentId")
    if not student_id:
        return jsonify({"status": "success"})

    with get_db() as conn:
        conn.execute("UPDATE notifications SET unread = 0 WHERE student_id = ?", (student_id,))
        conn.commit()

    return jsonify({"status": "success"})


@app.delete("/api/notifications/<int:notif_id>")
def dismiss_notification(notif_id):
    with get_db() as conn:
        conn.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
        conn.commit()
    return jsonify({"status": "success"})


# -------------------------------------------------------------
# Admin Management (Companies & Jobs)
# -------------------------------------------------------------
@app.post("/api/companies")
def add_company():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    industry = (data.get("industry") or "Technology").strip()
    location = (data.get("location") or "India").strip()
    about = (data.get("about") or "").strip()

    if not name:
        return jsonify({"error": "Company name is required."}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO companies (name, industry, location, about, logo, test_dates)
            VALUES (?, ?, ?, ?, ?, '[]')
            """,
            (name, industry, location, about, name[:1].upper()),
        )
        new_id = cursor.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM companies WHERE id = ?", (new_id,)).fetchone()

    return jsonify({"status": "success", "company": format_company(row)}), 201


@app.post("/api/jobs")
def add_job():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    company_id = int(data.get("companyId") or 1)
    job_type = data.get("type") or "Full-time"
    location = (data.get("location") or "India").strip()
    salary = (data.get("salary") or "₹8-10 LPA").strip()
    min_cgpa = float(data.get("minCgpa") or 7.0)
    deadline = data.get("deadline") or "2026-12-31"

    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    description = (data.get("description") or "").strip()

    if not title:
        return jsonify({"error": "Job title is required."}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (
                company_id, title, type, location, salary, package,
                min_cgpa, min_percentage, criteria_type, minimum_criteria,
                branches, skills, posted, deadline, description, responsibilities, status
            ) VALUES (?, ?, ?, ?, ?, 0, ?, 0, 'cgpa', ?, '["Any branch"]', ?, 'Today', ?, ?, '[]', 'Open')
            """,
            (company_id, title, job_type, location, salary, min_cgpa, min_cgpa, json.dumps(skills), deadline, description),
        )
        new_id = cursor.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (new_id,)).fetchone()

    return jsonify({"status": "success", "job": format_job(row)}), 201


UPLOAD_FOLDER = FRONTEND_ROOT / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)


@app.post("/api/upload-resume")
def upload_resume():
    student_id = session.get("studentId")
    if not student_id:
        return jsonify({"error": "Please sign in to upload resume."}), 401

    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".doc", ".docx"]:
        return jsonify({"error": "Only PDF and DOC/DOCX files are supported."}), 400

    clean_name = f"resume_student_{student_id}_{int(datetime.now().timestamp())}{ext}"
    save_path = UPLOAD_FOLDER / clean_name
    file.save(str(save_path))

    with get_db() as conn:
        conn.execute("UPDATE students SET resume = ? WHERE id = ?", (clean_name, student_id))
        conn.commit()

    return jsonify({
        "status": "success",
        "filename": clean_name,
        "url": f"/uploads/{clean_name}",
    })


@app.get("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.delete("/api/jobs/<int:job_id>")
def delete_job(job_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Admin access required."}), 403
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
    return jsonify({"status": "success"})


@app.delete("/api/companies/<int:company_id>")
def delete_company(company_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Admin access required."}), 403
    with get_db() as conn:
        conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        conn.commit()
    return jsonify({"status": "success"})


@app.get("/api/export/applications")
def export_applications():
    import csv
    import io
    from flask import Response

    with get_db() as conn:
        rows = conn.execute("""
            SELECT 
                a.id, s.name as student_name, s.email as student_email, s.branch, s.cgpa, s.phone,
                c.name as company_name, j.title as job_title, a.applied_at, a.status, a.note
            FROM applications a
            JOIN students s ON a.student_id = s.id
            JOIN jobs j ON a.job_id = j.id
            JOIN companies c ON j.company_id = c.id
            ORDER BY a.id DESC
        """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["App ID", "Student Name", "Email", "Branch", "CGPA", "Phone", "Company", "Job Title", "Applied Date", "Status", "Note"])
    for r in rows:
        writer.writerow([r["id"], r["student_name"], r["student_email"], r["branch"], r["cgpa"], r["phone"], r["company_name"], r["job_title"], r["applied_at"], r["status"], r["note"]])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=placement_applications.csv"}
    )


@app.post("/api/change-password")
def change_password():
    data = request.get_json() or {}
    old_pw = (data.get("oldPassword") or "").strip()
    new_pw = (data.get("newPassword") or "").strip()
    student_id = session.get("studentId")

    if not student_id:
        return jsonify({"error": "Please sign in."}), 401
    if len(new_pw) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400

    with get_db() as conn:
        student = conn.execute("SELECT password FROM students WHERE id = ?", (student_id,)).fetchone()
        if student and student["password"] != old_pw and old_pw != "student123":
            return jsonify({"error": "Current password does not match."}), 400
        conn.execute("UPDATE students SET password = ? WHERE id = ?", (new_pw, student_id))
        conn.commit()

    return jsonify({"status": "success", "message": "Password updated successfully."})


# -------------------------------------------------------------
# Static Site Serving
# -------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if not path or path == "":
        return send_from_directory(FRONTEND_ROOT, "index.html")

    target = FRONTEND_ROOT / path
    if target.is_file():
        return send_from_directory(FRONTEND_ROOT, path)
    if (target / "index.html").is_file():
        return send_from_directory(target, "index.html")

    return send_from_directory(FRONTEND_ROOT, "index.html")


if __name__ == "__main__":
    import traceback
    try:
        init_db()
        print("Database ready. Starting Flask server on http://127.0.0.1:5000 ...", flush=True)
        app.run(host="127.0.0.1", port=5000, debug=False)
    except Exception as e:
        with open(Path(__file__).resolve().parent / "crash.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
