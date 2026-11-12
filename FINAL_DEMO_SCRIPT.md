# Final Demonstration Script (Lab 39)

## 1. Architecture & System Health (1 min)
- Open `/system/health` in the browser to demonstrate live MySQL connectivity (`enrollment_system_db`), active table detection, and registered Flask routes.

## 2. Administrator Workflow (3 mins)
- Log in as Admin at `/login` -> show `/admin/dashboard`.
- Open `/students` -> demonstrate CSV Export (`students_report.csv`) and click Enroll on a student to open `/reports/student_enrollment`.
- Open `/reports/enrollment_summary` -> highlight live course enrollment totals.
- Open `/courses` -> show Course CRUD (`Add New Course`, `Edit`).

## 3. Student Workflow, COR & Statement of Account (2 mins)
- Log out and log in as a Student.
- Show `/student/dashboard`, open My COR (`/enrollment/confirmation/<id>`), and open My SOA (`/student/<id>/soa`) to demonstrate fee computation and balance tracking.

## 4. Security, Error Handling & QA Verification (2 mins)
- While logged in as a Student, attempt to visit `/admin/dashboard` or `/students` -> demonstrate `HTTP 403 Access Denied`.
- Visit `/nonexistent-page` -> demonstrate custom `HTTP 404 Page Not Found`.
- Run `python3 -m unittest discover -s tests -v` (10/10 passing tests) and `python3 backup_db.py`.
