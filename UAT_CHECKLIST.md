# User Acceptance Testing (UAT) & QA Sign-Off Checklist (Labs 33-34)

- [x] TC-01 (Authentication): Valid Admin and Student accounts authenticate and route to respective dashboards.
- [x] TC-02 (Session Enforcement): Unauthenticated requests redirect to `/login`.
- [x] TC-03 (RBAC Admin Protection): Student sessions accessing `/admin/dashboard`, `/students`, or `/courses` receive HTTP `403`.
- [x] TC-04 (RBAC Record Privacy): Student sessions accessing another student's SOA or COR receive HTTP `403`.
- [x] TC-05 (CSV Roster Operations): Export (`students_report.csv`) and bulk import work cleanly.
- [x] TC-06 (Reports & SOA): `/reports/student_enrollment`, `/reports/enrollment_summary`, and `/student/<id>/soa` render live data.
- [x] TC-07 (Health & Error Pages): `/system/health` returns `200 OK`; `403`, `404`, and `500` render custom templates.
