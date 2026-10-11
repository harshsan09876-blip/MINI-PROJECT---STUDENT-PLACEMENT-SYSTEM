"""SQLite persistence and seed data for the placement portal."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

from company import company_details
from placement import placement_drives
from student import students
from test_criteria import test_criteria

DATABASE_PATH = Path(__file__).resolve().parent.parent / "placement.db"

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  branch TEXT NOT NULL DEFAULT '',
  year TEXT NOT NULL DEFAULT '',
  percentage REAL NOT NULL DEFAULT 0,
  cgpa REAL NOT NULL DEFAULT 0,
  backlogs INTEGER NOT NULL DEFAULT 0,
  phone TEXT NOT NULL DEFAULT '',
  skills_json TEXT NOT NULL DEFAULT '[]',
  bio TEXT NOT NULL DEFAULT '',
  resume TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  industry TEXT NOT NULL DEFAULT '',
  location TEXT NOT NULL DEFAULT '',
  about TEXT NOT NULL DEFAULT '',
  logo TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  company_id INTEGER NOT NULL REFERENCES companies(id),
  type TEXT NOT NULL DEFAULT 'Full-time',
  location TEXT NOT NULL DEFAULT '',
  salary TEXT NOT NULL DEFAULT '',
  package REAL NOT NULL DEFAULT 0,
  min_cgpa REAL NOT NULL DEFAULT 0,
  min_percentage REAL NOT NULL DEFAULT 0,
  criteria_type TEXT NOT NULL DEFAULT 'cgpa',
  minimum_criteria REAL NOT NULL DEFAULT 0,
  branches_json TEXT NOT NULL DEFAULT '["Any branch"]',
  skills_json TEXT NOT NULL DEFAULT '[]',
  posted TEXT NOT NULL DEFAULT 'Today',
  deadline TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  responsibilities_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'Open'
);
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  applied_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Applied',
  note TEXT NOT NULL DEFAULT 'Your application was received.',
  UNIQUE(student_id, job_id)
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  time TEXT NOT NULL DEFAULT 'Just now',
  unread INTEGER NOT NULL DEFAULT 1,
  kind TEXT NOT NULL DEFAULT 'info'
);
CREATE TABLE IF NOT EXISTS saved_jobs (
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, job_id)
);
"""


@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _seed(connection):
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if not admin:
        connection.execute(
            "INSERT INTO users(email, password_hash, role) VALUES (?, ?, 'admin')",
            ("admin@pathway.demo", generate_password_hash("admin123")),
        )

    for index, person in enumerate(students, start=1):
        email = f"student{index}@placement.demo"
        existing = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            continue
        cursor = connection.execute(
            "INSERT INTO users(email, password_hash, role) VALUES (?, ?, 'student')",
            (email, generate_password_hash("student123")),
        )
        connection.execute(
            """INSERT INTO students(id, name, branch, year, percentage, cgpa, backlogs)
               VALUES (?, ?, ?, '2027', ?, ?, ?)""",
            (cursor.lastrowid, person["name"], person["branch"], person["percentage"], person["cgpa"], person["backlogs"]),
        )

    for name, details in company_details.items():
        connection.execute(
            """INSERT OR IGNORE INTO companies(name, industry, location, about, logo)
               VALUES (?, 'Technology', 'India', ?, ?)""",
            (name, details.get("criteria", "Placement partner"), name[:1].upper()),
        )

    existing_jobs = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if existing_jobs == 0:
        for drive in placement_drives:
            company_row = connection.execute("SELECT id FROM companies WHERE name = ?", (drive["company"],)).fetchone()
            company_info = company_details.get(drive["company"], {})
            # Keep seeding resilient if a drive is added before its company entry.
            if company_row is None:
                cursor = connection.execute(
                    "INSERT INTO companies(name, industry, location, about, logo) VALUES (?, ?, ?, ?, ?)",
                    (drive["company"], "Technology", "India", "Placement partner", drive["company"][:1].upper()),
                )
                company_id = cursor.lastrowid
            else:
                company_id = company_row["id"]
            criteria_type = drive["criteria_type"]
            minimum = float(drive["minimum_criteria"])
            deadline = (company_info.get("test_dates") or [date.today().isoformat()])[0]
            connection.execute(
                """INSERT INTO jobs(
                    title, company_id, type, location, salary, min_cgpa, min_percentage,
                    criteria_type, minimum_criteria, branches_json, skills_json, posted,
                    deadline, description, responsibilities_json
                ) VALUES (?, ?, 'Full-time', 'India', 'See placement cell', ?, ?, ?, ?, ?, ?, 'Current', ?, ?, '[]')""",
                (
                    drive["role"], company_id,
                    minimum if criteria_type == "cgpa" else 0,
                    minimum if criteria_type == "percentage" else 0,
                    criteria_type, minimum, json.dumps(["Any branch"]),
                    json.dumps(["Placement drive"]), deadline,
                    test_criteria.get(drive["company"], "Eligibility criteria available from the placement cell."),
                ),
            )


def init_db():
    with connect() as connection:
        connection.executescript(SCHEMA)
        _seed(connection)


def row_dict(row):
    return dict(row) if row else None


def student_dict(row):
    if not row:
        return None
    result = dict(row)
    result["skills"] = json.loads(result.pop("skills_json"))
    return result


def company_dict(row):
    return dict(row) if row else None


def job_dict(row):
    if not row:
        return None
    result = dict(row)
    result.update(
        {
            "companyId": result.pop("company_id"),
            "minCgpa": result.pop("min_cgpa"),
            "minPercentage": result.pop("min_percentage"),
            "criteriaType": result.pop("criteria_type"),
            "minimumCriteria": result.pop("minimum_criteria"),
            "branches": json.loads(result.pop("branches_json")),
            "skills": json.loads(result.pop("skills_json")),
            "responsibilities": json.loads(result.pop("responsibilities_json")),
        }
    )
    return result


def application_dict(row):
    if not row:
        return None
    result = dict(row)
    result["studentId"] = result.pop("student_id")
    result["jobId"] = result.pop("job_id")
    result["appliedAt"] = result.pop("applied_at")
    return result
