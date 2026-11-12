# Online Enrollment System - User Manual (Lab 38)

## 1. Role-Based Access
- Administrator (`role = admin`): Full access to dashboards, student roster, CSV import/export, courses, offerings, fee assessments, payments, and reports.
- Student (`role = student`): Restricted to personal dashboard, course enrollment, personal COR, and personal Statement of Account (SOA).

## 2. Administrator Guide
1. Login at `/login` with Administrator credentials.
2. Manage Students (`/students`): View student records, click Export CSV (`students_report.csv`), or upload a CSV file to bulk-import students.
3. Manage Courses (`/courses`): Add courses (`/courses/new`), update units/titles, or delete obsolete courses.
4. Reports:
   - Student Enrollment Report (`/reports/student_enrollment`)
   - Enrollment Summary (`/reports/enrollment_summary`)
5. Backup & Recovery:
   - Create snapshot: `python3 backup_db.py`
   - Restore latest snapshot: `python3 restore_db.py`

## 3. Student Guide
1. Login at `/login` using Student credentials.
2. Student Dashboard (`/student/dashboard`): Review enrolled load, total units, and balance summary.
3. Certificate of Registration (`/enrollment/confirmation/<id>`): View official subject registration.
4. Statement of Account (`/student/<id>/soa`): Inspect itemized tuition, miscellaneous fees, payment history, and remaining balance.
