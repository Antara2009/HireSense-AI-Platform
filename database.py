
import os
import sqlite3
from flask import g

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "database",
    "hiresense.db"
)


# Get database connection
def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        g.db = sqlite3.connect(DB_PATH, timeout=30)
        g.db.row_factory = sqlite3.Row

        g.db.execute("PRAGMA busy_timeout = 30000")
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


# Close database connection after each request
def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


# Initialize database and create tables
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=30)

    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student','company')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            department TEXT NOT NULL,
            location TEXT NOT NULL,
            skills TEXT NOT NULL,
            description TEXT NOT NULL,
            company_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            resume_filename TEXT NOT NULL,
            resume_path TEXT NOT NULL,
            resume_text TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            matched_skills TEXT,
            missing_skills TEXT,
            status TEXT NOT NULL DEFAULT 'Applied',
            decision_note TEXT,
            offer_letter_path TEXT,
            alternate_job_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, student_id),
            FOREIGN KEY(job_id) REFERENCES jobs(id),
            FOREIGN KEY(student_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            application_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(application_id) REFERENCES applications(id)
        );

        CREATE TABLE IF NOT EXISTS analyses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            target_role TEXT NOT NULL,
            score INTEGER NOT NULL,
            matched_skills TEXT,
            missing_skills TEXT,
            resume_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

        # Upgrade older databases safely
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(applications)"
            ).fetchall()
        }

        upgrades = {
            "decision_note": "TEXT",
            "offer_letter_path": "TEXT",
            "alternate_job_id": "INTEGER"
        }

        for name, definition in upgrades.items():
            if name not in columns:
                conn.execute(
                    f"ALTER TABLE applications ADD COLUMN {name} {definition}"
                )

        conn.commit()

    finally:
        conn.close()


# Add demo jobs if the jobs table is empty
def seed_data():
    conn = sqlite3.connect(DB_PATH, timeout=30)

    try:
        conn.execute("PRAGMA busy_timeout=30000")

        count = conn.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        if count == 0:
            sample_jobs = [
                (
                    "Python Developer",
                    "TechNova Solutions",
                    "Engineering",
                    "Pune / Hybrid",
                    "python, sql, flask, git, problem solving, rest api",
                    "Develop backend applications, build APIs, work with databases and collaborate with a software team."
                ),
                (
                    "Data Analyst",
                    "InsightWorks",
                    "Analytics",
                    "Remote",
                    "python, sql, excel, data analysis, statistics, power bi",
                    "Analyze datasets, prepare reports, create dashboards and communicate business insights."
                ),
                (
                    "Machine Learning Intern",
                    "Aster AI Labs",
                    "AI/ML",
                    "Bengaluru / Hybrid",
                    "python, machine learning, pandas, numpy, scikit-learn, statistics",
                    "Prepare datasets, train baseline ML models, evaluate results and document experiments."
                ),
                (
                    "Frontend Developer",
                    "PixelCraft Digital",
                    "Product",
                    "Mumbai",
                    "html, css, javascript, react, responsive design, git",
                    "Build accessible responsive interfaces and collaborate with designers and backend developers."
                ),
                (
                    "Java Developer",
                    "CoreStack Systems",
                    "Engineering",
                    "Pune",
                    "java, oops, sql, spring boot, git, problem solving",
                    "Develop and maintain Java services, write clean code and work with relational databases."
                )
            ]

            conn.executemany(
                """
                INSERT INTO jobs
                (title, company, department, location, skills, description)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                sample_jobs
            )

            conn.commit()

    finally:
        conn.close()
