# HireSense AI – Upgrade Build

A Flask + SQLite academic project for resume analysis, job matching and recruiter application screening.

## Features
- Minimal split-screen login landing page with scrollable product sections and developer credits.
- Role-based student/company registration and login.
- Hamburger navigation after login.
- Student resume analysis, job search, resume-based applications and application status tracking.
- Company vacancy posting, application statistics and Smart Screening ranked by explainable skill-match score.
- Recruiters can review/download submitted resumes and update candidate status.

## Run on Windows (PowerShell)
```powershell
cd HireSense_AI_Mini_Project
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```
Open http://127.0.0.1:5000

## Demo flow
1. Register a Company account and publish a vacancy.
2. Register a Student account and open Explore Jobs.
3. Apply to the vacancy with a PDF, DOCX or TXT resume.
4. Log in as the Company and open Smart Screening for that vacancy.

## Important notes
- Matching currently uses transparent rule-based skill matching, not a trained ML model or external LLM. Treat scores as decision-support only; recruiters must review candidates themselves.
- Seeded vacancies are demo data, not live job feeds.
- Uploaded application resumes are stored under `uploads/` so the owning recruiter can download them. Restrict server access and configure retention/deletion before public deployment.
- Set a strong `SECRET_KEY` environment variable before deployment.
- SQLite is suitable for this academic demo; use a managed database and secure file storage for production.

## Project credits
Designed & Developed by Nihal Kishor Sartape and Mayur Vinesh Ransingh.


## Recruitment decision workflow (upgrade)

Recruiters can now set an application to Applied, Under Review, Shortlisted, Selected, Rejected, or Alternate Position. Each decision creates an in-app notification for the student. For Alternate Position, the recruiter selects another active vacancy belonging to their company. For Selected, the recruiter may upload an offer letter PDF; the student can download it from the application tracker. Recruiters can also add a short decision note.

### Optional email delivery

In-app notifications work without external services. To send decision emails too, configure the SMTP environment variables shown in `.env.example` (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`). Never commit real credentials. If SMTP is not configured, the app still saves the decision and in-app notification.

### Important implementation note

Resume-to-job scoring in this version is explainable skills-overlap matching. It is not a trained machine-learning model and should be presented accurately during the project demonstration. Recruiters remain responsible for final hiring decisions.
