"""Database management and SQLite models for Student Placement System."""

import json
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "placement.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they do not exist and seed initial sample data."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                branch TEXT DEFAULT 'CSE',
                year TEXT DEFAULT '2027',
                cgpa REAL DEFAULT 0.0,
                percentage REAL DEFAULT 0.0,
                backlogs INTEGER DEFAULT 0,
                phone TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                bio TEXT DEFAULT '',
                resume TEXT DEFAULT ''
            )
        """)

        # 2. Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                industry TEXT DEFAULT 'Technology',
                location TEXT DEFAULT 'India',
                about TEXT DEFAULT '',
                logo TEXT DEFAULT '',
                test_dates TEXT DEFAULT '[]'
            )
        """)

        # 3. Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                type TEXT DEFAULT 'Full-time',
                location TEXT DEFAULT 'India',
                salary TEXT DEFAULT '₹8-10 LPA',
                package REAL DEFAULT 0,
                min_cgpa REAL DEFAULT 0,
                min_percentage REAL DEFAULT 0,
                criteria_type TEXT DEFAULT 'cgpa',
                minimum_criteria REAL DEFAULT 0,
                branches TEXT DEFAULT '["Any branch"]',
                skills TEXT DEFAULT '["Python"]',
                posted TEXT DEFAULT 'Current',
                deadline TEXT DEFAULT '2026-12-31',
                description TEXT DEFAULT '',
                responsibilities TEXT DEFAULT '[]',
                status TEXT DEFAULT 'Open',
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)

        # 4. Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                applied_at TEXT NOT NULL,
                status TEXT DEFAULT 'Applied',
                note TEXT DEFAULT 'Your application was received.',
                UNIQUE(student_id, job_id),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)

        # 5. Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                time TEXT NOT NULL,
                unread INTEGER DEFAULT 1,
                kind TEXT DEFAULT 'info',
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)

        # 6. Admins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT DEFAULT 'Placement Officer'
            )
        """)

        # 7. Saved jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                UNIQUE(student_id, job_id),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)

        # Seed Admin if not exists
        cursor.execute("SELECT id FROM admins WHERE email = 'admin@pathway.demo'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO admins (email, password, name) VALUES (?, ?, ?)",
                ("admin@pathway.demo", "admin123", "Placement Officer")
            )

        # Seed Companies if empty
        cursor.execute("SELECT COUNT(*) FROM companies")
        if cursor.fetchone()[0] == 0:
            sample_companies = [
                ("TCS", "Technology", "Mumbai, India", "Minimum 60%", "T", json.dumps(["2026-10-15", "2026-10-20"])),
                ("Infosys", "Technology", "Bengaluru, India", "Minimum 65%", "I", json.dumps(["2026-10-18", "2026-10-22"])),
                ("Google", "Technology", "Bengaluru, India", "Minimum 8.0 CGPA", "G", json.dumps(["2026-10-25", "2026-10-30"])),
                ("Microsoft", "Technology", "Hyderabad, India", "Minimum 8.5 CGPA", "M", json.dumps(["2026-11-01", "2026-11-05"])),
                ("Learn to Earn Lab", "EdTech", "Delhi, India", "Minimum 7.5 CGPA", "L", json.dumps(["2026-11-03", "2026-11-07"]))
            ]
            cursor.executemany(
                "INSERT INTO companies (name, industry, location, about, logo, test_dates) VALUES (?, ?, ?, ?, ?, ?)",
                sample_companies
            )

        # Seed Students if empty
        cursor.execute("SELECT COUNT(*) FROM students")
        if cursor.fetchone()[0] == 0:
            sample_students = [
                (
                    "Harsh Chauhan", "harsh@placement.demo", "password123", "CSE", "2027",
                    8.0, 75.0, 0, "+91 98765 00001",
                    json.dumps(["Python", "C++", "SQL"]), "CSE student aiming for software engineering roles.", ""
                ),
                (
                    "Jatin Chaudhary", "jatin@placement.demo", "password123", "CSE", "2027",
                    7.5, 72.0, 0, "+91 98765 00002",
                    json.dumps(["Java", "Web Development"]), "Interested in frontend and backend systems.", ""
                ),
                (
                    "Avi Singh", "avi@placement.demo", "password123", "CSE", "2027",
                    7.2, 68.0, 0, "+91 98765 00003",
                    json.dumps(["Python", "Data Analysis"]), "Passionate about data and automation.", ""
                ),
                (
                    "Rajeev Kumar", "rajeev@placement.demo", "password123", "CSE", "2027",
                    7.0, 65.0, 0, "+91 98765 00004",
                    json.dumps(["C", "Data Structures"]), "Focused on core problem solving and DSA.", ""
                ),
                (
                    "Aarav Mehta", "aarav@example.com", "password123", "Artificial Intelligence & Machine Learning", "2027",
                    8.4, 80.0, 0, "+91 98765 43210",
                    json.dumps(["Python", "JavaScript", "SQL"]), "AI & ML student interested in building useful products.", "Aarav_Mehta_Resume.pdf"
                ),
                (
                    "Demo Student", "student1@placement.demo", "student123", "Computer Science", "2027",
                    8.5, 80.75, 0, "+91 98765 11111",
                    json.dumps(["Python", "Web Development", "SQL"]), "Aspiring software engineer.", ""
                )
            ]
            cursor.executemany("""
                INSERT INTO students (name, email, password, branch, year, cgpa, percentage, backlogs, phone, skills, bio, resume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_students)

        # Seed Jobs if empty
        cursor.execute("SELECT COUNT(*) FROM jobs")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id, name FROM companies")
            company_map = {name: cid for cid, name in cursor.fetchall()}

            sample_jobs = [
                (
                    company_map.get("TCS", 1), "Software Developer", "Full-time", "Mumbai · Hybrid",
                    "₹7-9 LPA", 8.0, 0.0, 60.0, "percentage", 60.0,
                    json.dumps(["CSE", "IT", "ECE"]), json.dumps(["Java", "C++", "SQL"]),
                    "Current", "2026-10-20", "Minimum 60% required in 10th, 12th and Graduation. No active backlogs.",
                    json.dumps(["Build scalable software", "Collaborate with team", "Participate in code reviews"]), "Open"
                ),
                (
                    company_map.get("Infosys", 2), "System Engineer", "Full-time", "Bengaluru · On-site",
                    "₹8-10 LPA", 9.5, 0.0, 65.0, "percentage", 65.0,
                    json.dumps(["CSE", "IT"]), json.dumps(["Python", "Java", "DSA"]),
                    "Current", "2026-10-22", "Minimum 65% aggregate required. Strong fundamental programming skills.",
                    json.dumps(["Develop robust modules", "Fix bugs and enhance system performance"]), "Open"
                ),
                (
                    company_map.get("Google", 3), "Software Engineer", "Full-time", "Bengaluru · Hybrid",
                    "₹25-30 LPA", 28.0, 8.0, 0.0, "cgpa", 8.0,
                    json.dumps(["CSE", "AI/ML", "IT"]), json.dumps(["DSA", "Algorithms", "C++", "Python"]),
                    "Current", "2026-10-30", "Minimum 8.0 CGPA required. Exceptional algorithmic and problem-solving skills.",
                    json.dumps(["Design large-scale systems", "Develop high-throughput services", "Improve reliability"]), "Open"
                ),
                (
                    company_map.get("Microsoft", 4), "Software Engineer", "Full-time", "Hyderabad · Hybrid",
                    "₹24-28 LPA", 26.0, 8.5, 0.0, "cgpa", 8.5,
                    json.dumps(["CSE", "IT"]), json.dumps(["C#", "Azure", "Algorithms", "DSA"]),
                    "Current", "2026-11-05", "Minimum 8.5 CGPA required. Strong grasp of computer science fundamentals.",
                    json.dumps(["Architect cloud-native microservices", "Ship high quality customer features"]), "Open"
                ),
                (
                    company_map.get("Learn to Earn Lab", 5), "Software Developer", "Full-time", "Delhi · Remote",
                    "₹10-12 LPA", 11.0, 7.5, 0.0, "cgpa", 7.5,
                    json.dumps(["Any branch"]), json.dumps(["Python", "Flask", "React", "SQL"]),
                    "Current", "2026-11-07", "Minimum 7.5 CGPA required. Practical web development and problem-solving skills.",
                    json.dumps(["Work on full stack web applications", "Build APIs and frontends"]), "Open"
                )
            ]
            cursor.executemany("""
                INSERT INTO jobs (
                    company_id, title, type, location, salary, package,
                    min_cgpa, min_percentage, criteria_type, minimum_criteria,
                    branches, skills, posted, deadline, description, responsibilities, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_jobs)

        # Seed sample notifications
        cursor.execute("SELECT COUNT(*) FROM notifications")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id FROM students LIMIT 1")
            first_student = cursor.fetchone()
            sid = first_student[0] if first_student else 1
            cursor.executemany("""
                INSERT INTO notifications (student_id, title, body, time, unread, kind)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (sid, "Welcome to Placement Portal", "Your profile is registered. Explore campus placement drives.", "Just now", 1, "info"),
                (sid, "New Drive Announced", "Google campus drive is open for eligible students.", "1 hour ago", 1, "success")
            ])

        conn.commit()


# Helper query methods
def format_student(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "branch": row["branch"],
        "year": row["year"],
        "cgpa": float(row["cgpa"] or 0),
        "percentage": float(row["percentage"] or 0),
        "backlogs": int(row["backlogs"] or 0),
        "phone": row["phone"] or "",
        "skills": json.loads(row["skills"]) if row["skills"] else [],
        "bio": row["bio"] or "",
        "resume": row["resume"] or ""
    }


def format_company(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "industry": row["industry"],
        "location": row["location"],
        "about": row["about"],
        "logo": row["logo"] or row["name"][:1].upper(),
        "testDates": json.loads(row["test_dates"]) if row["test_dates"] else []
    }


def format_job(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "companyId": row["company_id"],
        "type": row["type"],
        "location": row["location"],
        "salary": row["salary"],
        "package": float(row["package"] or 0),
        "minCgpa": float(row["min_cgpa"] or 0),
        "minPercentage": float(row["min_percentage"] or 0),
        "criteriaType": row["criteria_type"],
        "minimumCriteria": float(row["minimum_criteria"] or 0),
        "branches": json.loads(row["branches"]) if row["branches"] else ["Any branch"],
        "skills": json.loads(row["skills"]) if row["skills"] else [],
        "posted": row["posted"],
        "deadline": row["deadline"],
        "description": row["description"],
        "responsibilities": json.loads(row["responsibilities"]) if row["responsibilities"] else [],
        "status": row["status"]
    }


def format_application(row):
    return {
        "id": row["id"],
        "studentId": row["student_id"],
        "jobId": row["job_id"],
        "appliedAt": row["applied_at"],
        "status": row["status"],
        "note": row["note"]
    }
