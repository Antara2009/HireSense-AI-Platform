# HireSense AI Upgrade Notes

Changes included in this package:
- Added a homepage feature/research slider with previous/next and dot navigation.
- Kept the green-and-white visual direction and hamburger navigation.
- Added recruiter decision stages: Applied, Under Review, Shortlisted, Selected, Rejected, Alternate Position.
- Added optional recruiter notes on each decision.
- Added student in-app notifications and mark-as-read action.
- Added alternate vacancy selection, limited to another active vacancy from the same company.
- Added optional PDF offer-letter upload for selected candidates and a student download link.
- Added optional SMTP email delivery configured through environment variables. In-app notifications work without SMTP.
- Added safe SQLite schema migration for existing databases.

Validation performed: Python source compilation, JavaScript syntax check, Jinja template parsing, and SQLite schema initialization.

Not verified in this environment: full browser interaction or real SMTP delivery. Flask dependencies are listed in requirements.txt and must be installed locally before running the app.
