import os
import io
import re
import csv
import uuid
from datetime import datetime
from functools import wraps
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'enrollment_system_prod_secret_2026')

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='admin1234',
        database='enrollment_system_db',
        port=3306
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'admin')
            flash('Logged in successfully!', 'success')
            return redirect(url_for('students'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))



@app.route('/students')
@login_required
def students():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = request.args.get('q', '').strip()
    program_id = request.args.get('program_id', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page

    where_clauses = []
    params = []

    if query:
        where_clauses.append("(s.first_name LIKE %s OR s.last_name LIKE %s OR CONCAT(s.first_name, ' ', s.last_name) LIKE %s OR s.student_number LIKE %s OR s.email LIKE %s)")
        search_term = f"%{query}%"
        params.extend([search_term, search_term, search_term, search_term, search_term])

    if program_id:
        where_clauses.append("s.program_id = %s")
        params.append(program_id)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    count_sql = f"SELECT COUNT(*) AS total FROM students s{where_sql}"
    cursor.execute(count_sql, tuple(params))
    total_count = cursor.fetchone()['total']

    data_sql = f"""
        SELECT s.*, p.program_name, p.program_code 
        FROM students s 
        LEFT JOIN programs p ON s.program_id = p.program_id
        {where_sql}
        ORDER BY s.student_id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([per_page, offset])
    cursor.execute(data_sql, tuple(params))
    students_list = cursor.fetchall()

    cursor.execute("SELECT * FROM programs")
    programs = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return render_template(
        'students.html',
        students=students_list,
        programs=programs,
        query=query,
        selected_program=program_id,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )

@app.route('/student/new', methods=['GET', 'POST'])
@login_required
def student_new():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_number = request.form['student_number']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        program_id = request.form.get('program_id') or None

        profile_image = 'default_avatar.png'
        file = request.files.get('profile_image')
        if file and file.filename != '' and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            profile_image = filename

        cursor.execute(
            "INSERT INTO students (student_number, first_name, last_name, email, program_id, profile_image) VALUES (%s, %s, %s, %s, %s, %s)",
            (student_number, first_name, last_name, email, program_id, profile_image)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash('Student added successfully!', 'success')
        return redirect(url_for('students'))

    cursor.execute("SELECT * FROM programs")
    programs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('student_form.html', programs=programs)

@app.route('/student/<int:student_id>')
@login_required
def student_profile(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    cursor.execute("""SELECT e.*, c.course_code, c.course_code AS course_name, c.units
        FROM enrollments e
        JOIN course_offerings co ON e.offering_id = co.offering_id
        JOIN courses c ON co.course_id = c.course_id
        WHERE e.student_id = %s""", (student_id,))
    enrolled_courses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('student_profile.html', student=student, enrolled_courses=enrolled_courses)




# ----------------------------------------------------
# Dashboards & Statement of Account (Labs 24-25 & SOA)
# ----------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role', 'admin')
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM courses")
    total_courses = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM course_offerings")
    total_offerings = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM enrollments")
    total_enrollments = cursor.fetchone()['total']

    cursor.close()
    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        total_courses=total_courses,
        total_offerings=total_offerings,
        total_enrollments=total_enrollments
    )

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    user_id = session.get('user_id')
    student_id = session.get('student_id')

    if not student_id and user_id:
        cursor.execute("SELECT student_id FROM users WHERE user_id = %s", (user_id,))
        u = cursor.fetchone()
        if u and u.get('student_id'):
            student_id = u['student_id']

    student = None
    enrolled_courses = []

    if student_id:
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()

        cursor.execute("SHOW COLUMNS FROM courses")
        c_cols = [c['Field'] for c in cursor.fetchall()]
        title_col = 'course_title' if 'course_title' in c_cols else ('course_name' if 'course_name' in c_cols else 'title')

        cursor.execute(f"""
            SELECT e.enrollment_id, c.course_code, c.{title_col} AS course_title,
                   e.enrollment_date
            FROM enrollments e
            JOIN course_offerings co ON e.offering_id = co.offering_id
            JOIN courses c ON co.course_id = c.course_id
            WHERE e.student_id = %s
        """, (student_id,))
        enrolled_courses = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM students LIMIT 1")
        student = cursor.fetchone()
        if student:
            student_id = student['student_id']
            cursor.execute("SHOW COLUMNS FROM courses")
            c_cols = [c['Field'] for c in cursor.fetchall()]
            title_col = 'course_title' if 'course_title' in c_cols else ('course_name' if 'course_name' in c_cols else 'title')

            cursor.execute(f"""
                SELECT e.enrollment_id, c.course_code, c.{title_col} AS course_title,
                       e.enrollment_date
                FROM enrollments e
                JOIN course_offerings co ON e.offering_id = co.offering_id
                JOIN courses c ON co.course_id = c.course_id
                WHERE e.student_id = %s
            """, (student_id,))
            enrolled_courses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'student_dashboard.html',
        student=student,
        enrolled_courses=enrolled_courses
    )



@app.route('/student/<int:student_id>/soa')
@app.route('/statement_of_account/<int:student_id>')
@login_required
def statement_of_account(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.*, p.program_name, p.program_code 
            FROM students s 
            LEFT JOIN programs p ON s.program_id = p.program_id 
            WHERE s.student_id = %s
        """, (student_id,))
        student = cursor.fetchone()
    except Exception:
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()

    if not student:
        cursor.close()
        conn.close()
        flash('Student record not found.', 'danger')
        return redirect(url_for('students'))

    cursor.execute("""
        SELECT * FROM enrollments 
        WHERE student_id = %s 
        ORDER BY enrollment_id DESC LIMIT 1
    """, (student_id,))
    enrollment = cursor.fetchone()

    enrolled_courses = []
    total_units = 0
    tuition_fee = 0
    miscellaneous_fee = 0
    grand_total = 0
    total_paid = 0
    balance_due = 0

    if enrollment:
        try:
            cursor.execute("""
                SELECT co.*, c.course_code, 
                       COALESCE(c.course_title, c.course_code) AS course_title,
                       COALESCE(c.units, 3) AS units 
                FROM enrollment_items ei 
                JOIN course_offerings co ON ei.offering_id = co.offering_id 
                JOIN courses c ON co.course_id = c.course_id 
                WHERE ei.enrollment_id = %s
            """, (enrollment['enrollment_id'],))
            enrolled_courses = cursor.fetchall()
        except Exception:
            cursor.execute("""
                SELECT co.*, c.course_code, 
                       COALESCE(c.course_title, c.course_code) AS course_title,
                       COALESCE(c.units, 3) AS units 
                FROM enrollments e 
                JOIN course_offerings co ON e.offering_id = co.offering_id 
                JOIN courses c ON co.course_id = c.course_id 
                WHERE e.enrollment_id = %s
            """, (enrollment['enrollment_id'],))
            enrolled_courses = cursor.fetchall()

        total_units = sum(item.get('units', 3) or 3 for item in enrolled_courses)
        tuition_fee = total_units * 500
        miscellaneous_fee = 1500
        grand_total = tuition_fee + miscellaneous_fee

        try:
            cursor.execute("""
                SELECT IFNULL(SUM(amount), 0) AS total_paid 
                FROM payments 
                WHERE enrollment_id = %s
            """, (enrollment['enrollment_id'],))
            res = cursor.fetchone()
            total_paid = res['total_paid'] if res else 0
        except Exception:
            total_paid = 0

        balance_due = grand_total - total_paid

    payments_history = []
    try:
        cursor.execute("""
            SELECT p.* 
            FROM payments p 
            JOIN enrollments e ON p.enrollment_id = e.enrollment_id 
            WHERE e.student_id = %s 
            ORDER BY p.payment_id DESC
        """, (student_id,))
        payments_history = cursor.fetchall()
    except Exception:
        payments_history = []

    cursor.close()
    conn.close()

    return render_template(
        'statement_of_account.html',
        student=student,
        enrollment=enrollment,
        courses=enrolled_courses,
        total_units=total_units,
        tuition_fee=tuition_fee,
        miscellaneous_fee=miscellaneous_fee,
        grand_total=grand_total,
        total_paid=total_paid,
        balance_due=balance_due,
        payments=payments_history
    )




@app.route('/courses', endpoint='courses')
@login_required
def courses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM courses")
    courses_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('courses.html', courses=courses_list)




@app.route('/course_offerings', endpoint='course_offerings')
@app.route('/offerings')
@login_required
def course_offerings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT co.*, c.course_code, COALESCE(c.course_title, c.course_code) AS course_title 
            FROM course_offerings co 
            JOIN courses c ON co.course_id = c.course_id
        """)
        offerings = cursor.fetchall()
    except Exception:
        offerings = []
    cursor.close()
    conn.close()
    return render_template('course_offerings.html', offerings=offerings)




@app.route('/export_students_csv', endpoint='export_students_csv')
@app.route('/students/export_csv')
@login_required
def export_students_csv():
    import csv
    import io
    from flask import Response

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students")
    students_data = cursor.fetchall()
    cursor.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    if students_data:
        writer.writerow(list(students_data[0].keys()))
        for row in students_data:
            writer.writerow(list(row.values()))
    else:
        writer.writerow(["student_id", "first_name", "last_name", "email", "program_id"])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=students_report.csv"
    return response




@app.route('/import_students_csv', methods=['POST'], endpoint='import_students_csv')
@app.route('/students/import_csv', methods=['POST'])
@login_required
def import_students_csv():
    import csv
    import io

    # Check for file in request
    uploaded_file = None
    for key in request.files:
        if request.files[key].filename != '':
            uploaded_file = request.files[key]
            break

    if not uploaded_file:
        flash('No CSV file selected for import.', 'warning')
        return redirect(url_for('students'))

    try:
        stream = io.StringIO(uploaded_file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        count = 0
        
        for row in csv_reader:
            first_name = row.get('first_name') or row.get('First Name') or row.get('firstname') or ''
            last_name = row.get('last_name') or row.get('Last Name') or row.get('lastname') or ''
            email = row.get('email') or row.get('Email') or ''
            program_id = row.get('program_id') or row.get('Program ID') or None
            
            first_name = first_name.strip()
            last_name = last_name.strip()
            email = email.strip()

            if first_name and last_name:
                try:
                    cursor.execute("""
                        INSERT INTO students (first_name, last_name, email, program_id)
                        VALUES (%s, %s, %s, %s)
                    """, (first_name, last_name, email, program_id if program_id else None))
                    count += 1
                except Exception as err:
                    print("Row import skipped/error:", err)

        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Successfully imported {count} student records from CSV!', 'success')
    except Exception as e:
        flash(f'Error processing CSV file: {str(e)}', 'danger')

    return redirect(url_for('students'))





@app.route('/courses/new', methods=['GET', 'POST'], endpoint='course_new')
@app.route('/courses/add', methods=['GET', 'POST'])
@login_required
def course_new():
    if request.method == 'POST':
        code = request.form.get('course_code')
        title = request.form.get('course_title')
        units = request.form.get('units', 3)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO courses (course_code, course_title, units) VALUES (%s, %s, %s)", (code, title, units))
            conn.commit()
            flash('Course added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding course: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('courses'))
    return render_template('course_form.html')




@app.route('/student/<int:student_id>/enrollment', endpoint='student_enrollment')
@app.route('/enrollment/<int:student_id>')
@login_required
def student_enrollment_action(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('students'))
        
    return redirect(f'/reports/student_enrollment?student_id={student_id}')




@app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'], endpoint='course_edit')
@login_required
def course_edit(course_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        code = request.form.get('course_code')
        title = request.form.get('course_title')
        units = request.form.get('units', 3)
        try:
            cursor.execute("""
                UPDATE courses 
                SET course_code = %s, course_title = %s, units = %s 
                WHERE course_id = %s
            """, (code, title, units, course_id))
            conn.commit()
            flash('Course updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating course: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('courses'))

    cursor.execute("SELECT * FROM courses WHERE course_id = %s", (course_id,))
    course = cursor.fetchone()
    cursor.close()
    conn.close()
    if not course:
        flash('Course record not found.', 'danger')
        return redirect(url_for('courses'))
    return render_template('course_form.html', course=course)

@app.route('/courses/<int:course_id>/delete', methods=['POST', 'GET'], endpoint='course_delete')
@login_required
def course_delete(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        conn.commit()
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting course: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('courses'))




@app.route('/reports/student_enrollment', endpoint='student_enrollment_report')
@login_required
def student_enrollment_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM students ORDER BY last_name, first_name")
    students_list = cursor.fetchall()
    
    student_id = request.args.get('student_id', type=int)
    selected_student = None
    enrolled_courses = []
    
    if student_id:
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        selected_student = cursor.fetchone()
        
        if selected_student:
            try:
                cursor.execute("""
                    SELECT e.enrollment_id, e.enrollment_date, c.course_code, 
                           COALESCE(c.course_title, c.course_code) AS course_title, 
                           COALESCE(c.units, 3) AS units
                    FROM enrollments e
                    JOIN course_offerings co ON e.offering_id = co.offering_id
                    JOIN courses c ON co.course_id = c.course_id
                    WHERE e.student_id = %s
                """, (student_id,))
                enrolled_courses = cursor.fetchall()
            except Exception:
                try:
                    cursor.execute("""
                        SELECT e.enrollment_id, e.enrollment_date, c.course_code,
                               COALESCE(c.course_title, c.course_code) AS course_title,
                               COALESCE(c.units, 3) AS units
                        FROM enrollment_items ei
                        JOIN enrollments e ON ei.enrollment_id = e.enrollment_id
                        JOIN course_offerings co ON ei.offering_id = co.offering_id
                        JOIN courses c ON co.course_id = c.course_id
                        WHERE e.student_id = %s
                    """, (student_id,))
                    enrolled_courses = cursor.fetchall()
                except Exception:
                    enrolled_courses = []
                
    cursor.close()
    conn.close()
    
    return render_template(
        'student_enrollment_report.html',
        students=students_list,
        selected_student=selected_student,
        enrolled_courses=enrolled_courses,
        student_id=student_id
    )




# ==============================================================================
# LABS 26-29: RBAC GUARD, COMPLETE INTEGRATION HEALTH CHECK & ERROR HANDLERS
# ==============================================================================

@app.before_request
def enforce_rbac_and_session():
    public_prefixes = ('/login', '/register', '/logout', '/static', '/system/health')
    path = request.path

    if path == '/' or path.startswith(public_prefixes):
        return None

    role = session.get('role')
    user_id = session.get('user_id')

    if not role and not user_id:
        return redirect('/login')

    # Restrict student accounts from accessing admin-only modules (Lab 27)
    admin_only_prefixes = (
        '/admin',
        '/students',
        '/courses',
        '/course_offerings',
        '/offerings',
        '/reports',
        '/export_students_csv',
        '/import_students_csv',
        '/fees'
    )
    if role == 'student' and path.startswith(admin_only_prefixes):
        abort(403)

    # Prevent students from viewing another student's profile, COR, or SOA
    if role == 'student' and session.get('student_id'):
        own_id = int(session.get('student_id'))
        match = re.search(r'/(?:student|statement_of_account|enrollment/confirmation|enrollment)/(\d+)', path)
        if match:
            target_id = int(match.group(1))
            if target_id != own_id:
                abort(403)


@app.route('/system/health')
def system_health():
    from flask import jsonify
    db_status = "disconnected"
    tables_count = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        tables_count = len(tables)
        db_status = "connected"
        cursor.close()
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify({
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "tables_detected": tables_count,
        "registered_routes": len(app.url_map._rules)
    })


@app.errorhandler(403)
def forbidden_error(e):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found_error(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500




@app.route('/reports/enrollment_summary', endpoint='enrollment_summary_report')
@login_required
def enrollment_summary_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    stats = {'total_students': 0, 'total_courses': 0, 'total_offerings': 0, 'total_enrollments': 0}
    course_summary = []

    for key, table in [('total_students', 'students'), ('total_courses', 'courses'),
                       ('total_offerings', 'course_offerings'), ('total_enrollments', 'enrollments')]:
        try:
            cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
            stats[key] = cursor.fetchone()['cnt']
        except Exception:
            pass

    try:
        cursor.execute("""
            SELECT c.course_code,
                   COALESCE(c.course_title, c.course_code) AS course_title,
                   COALESCE(c.units, 3) AS units,
                   COUNT(e.enrollment_id) AS enrolled_count
            FROM courses c
            LEFT JOIN course_offerings co ON c.course_id = co.course_id
            LEFT JOIN enrollments e ON co.offering_id = e.offering_id
            GROUP BY c.course_id, c.course_code, c.course_title, c.units
            ORDER BY c.course_code
        """)
        course_summary = cursor.fetchall()
    except Exception:
        course_summary = []

    cursor.close()
    conn.close()
    return render_template('enrollment_summary.html', stats=stats, course_summary=course_summary)




@app.route('/enrollment/confirmation/<int:student_id>', endpoint='enrollment_confirmation')
@login_required
def enrollment_confirmation(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Look up by student_id first
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    # 2. Fallback: if student_id was actually an enrollment_id, resolve the student
    if not student:
        try:
            cursor.execute("""
                SELECT s.* FROM students s
                JOIN enrollments e ON s.student_id = e.student_id
                WHERE e.enrollment_id = %s
            """, (student_id,))
            student = cursor.fetchone()
        except Exception:
            student = None

    if not student:
        cursor.close()
        conn.close()
        abort(404)

    actual_student_id = student['student_id']
    enrolled_courses = []

    try:
        cursor.execute("""
            SELECT e.enrollment_id, e.enrollment_date, c.course_code,
                   COALESCE(c.course_title, c.course_code) AS course_title,
                   COALESCE(c.units, 3) AS units
            FROM enrollments e
            JOIN course_offerings co ON e.offering_id = co.offering_id
            JOIN courses c ON co.course_id = c.course_id
            WHERE e.student_id = %s
        """, (actual_student_id,))
        enrolled_courses = cursor.fetchall()
    except Exception:
        try:
            cursor.execute("""
                SELECT e.enrollment_id, e.enrollment_date, c.course_code,
                       COALESCE(c.course_title, c.course_code) AS course_title,
                       COALESCE(c.units, 3) AS units
                FROM enrollment_items ei
                JOIN enrollments e ON ei.enrollment_id = e.enrollment_id
                JOIN course_offerings co ON ei.offering_id = co.offering_id
                JOIN courses c ON co.course_id = c.course_id
                WHERE e.student_id = %s
            """, (actual_student_id,))
            enrolled_courses = cursor.fetchall()
        except Exception:
            enrolled_courses = []

    total_units = sum(int(row.get('units') or 3) for row in enrolled_courses)

    cursor.close()
    conn.close()

    return render_template(
        'enrollment_confirmation.html',
        student=student,
        enrolled_courses=enrolled_courses,
        total_units=total_units
    )


if __name__ == '__main__':
    app.run(debug=True, port=5001)
