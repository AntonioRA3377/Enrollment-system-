import os
import io
import re
import csv
import uuid
from datetime import datetime
from functools import wraps
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

app = Flask(__name__)
app.secret_key = 'super_secret_key'

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


@app.route('/statement_of_account/<int:student_id>')
@login_required
def statement_of_account(student_id):
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

    total_units = sum(float(item.get('units') or 0) for item in enrolled_courses)
    rate_per_unit = 1500.00
    tuition_fee = total_units * rate_per_unit
    misc_fee = 2500.00 if total_units > 0 else 0.00
    total_amount = tuition_fee + misc_fee
    amount_paid = 0.00
    balance_due = total_amount - amount_paid

    return render_template(
        'statement_of_account.html',
        student=student,
        enrolled_courses=enrolled_courses,
        total_units=total_units,
        rate_per_unit=rate_per_unit,
        tuition_fee=tuition_fee,
        misc_fee=misc_fee,
        miscellaneous_fee=misc_fee,
        total_amount=total_amount,
        total_fee=total_amount,
        grand_total=total_amount,
        amount_paid=amount_paid,
        total_paid=amount_paid,
        balance_due=balance_due
    )


@app.route('/statement_of_account/<int:student_id>/pdf')
@login_required
def statement_of_account_pdf(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT s.*, p.program_name, p.program_code FROM students s LEFT JOIN programs p ON s.program_id = p.program_id WHERE s.student_id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    cursor.execute("""
        SELECT e.*, co.section, c.course_code, c.units, c.tuition_fee
        FROM enrollments e
        JOIN courses c ON e.course_id = c.course_id
        JOIN courses c ON co.course_id = c.course_id
        WHERE e.student_id = %s
    """, (student_id,))
    enrolled_courses = cursor.fetchall()

    total_units = sum(c['units'] for c in enrolled_courses) if enrolled_courses else 0
    tuition_fee = sum(c['tuition_fee'] for c in enrolled_courses) if enrolled_courses else 0.0
    miscellaneous_fee = 1500.00 if enrolled_courses else 0.0
    grand_total = tuition_fee + miscellaneous_fee

    cursor.execute("""
        SELECT p.*, e.enrollment_id 
        FROM payments p
        JOIN enrollments e ON p.enrollment_id = e.enrollment_id
        WHERE e.student_id = %s
        ORDER BY p.payment_id DESC
    """, (student_id,))
    payments_history = cursor.fetchall()

    total_paid = sum(p['amount_paid'] for p in payments_history) if payments_history else 0.0
    balance_due = grand_total - total_paid

    cursor.close()
    conn.close()

    rendered_html = render_template(
        'statement_of_account_pdf.html',
        student=student,
        courses=enrolled_courses,
        total_units=total_units,
        tuition_fee=tuition_fee,
        miscellaneous_fee=miscellaneous_fee,
        grand_total=grand_total,
        total_paid=total_paid,
        balance_due=balance_due,
        payments=payments_history,
        today=datetime.now().strftime('%B %d, %Y')
    )

    pdf_stream = io.BytesIO()
    pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_stream)

    if pisa_status.err:
        flash('Error generating PDF report.', 'danger')
        return redirect(url_for('statement_of_account', student_id=student_id))

    pdf_stream.seek(0)
    filename = f"SOA_{student['student_number']}.pdf"
    return send_file(pdf_stream, download_name=filename, as_attachment=True, mimetype='application/pdf')

@app.route('/students/export/csv')
@login_required
def export_students_csv():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.student_number, s.first_name, s.last_name, s.email, p.program_code 
        FROM students s 
        LEFT JOIN programs p ON s.program_id = p.program_id
        ORDER BY s.student_id ASC
    """)
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Number', 'First Name', 'Last Name', 'Email', 'Program Code'])

    for s in students:
        writer.writerow([s['student_number'], s['first_name'], s['last_name'], s['email'], s['program_code'] or 'Unassigned'])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=students_roster.csv'}
    )

@app.route('/students/import/csv', methods=['POST'])
@login_required
def import_students_csv():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'danger')
        return redirect(url_for('students'))

    stream = io.StringIO(file.stream.read().decode('utf-8-sig'), newline=None)
    csv_reader = csv.DictReader(stream)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT program_id, LOWER(program_code) AS code FROM programs")
    prog_map = {row['code']: row['program_id'] for row in cursor.fetchall()}

    imported_count = 0
    for row in csv_reader:
        clean_row = {re.sub(r'[^a-z0-9]', '', str(k).lower()): str(v).strip() for k, v in row.items() if k}

        student_num = clean_row.get('studentnumber') or clean_row.get('studentnum') or clean_row.get('studentno')
        first_name = clean_row.get('firstname') or clean_row.get('first')
        last_name = clean_row.get('lastname') or clean_row.get('last')
        email = clean_row.get('email')
        code = (clean_row.get('programcode') or clean_row.get('program') or '').lower()

        if student_num and first_name and last_name and email:
            p_id = prog_map.get(code, None)
            try:
                cursor.execute(
                    "INSERT INTO students (student_number, first_name, last_name, email, program_id, profile_image) VALUES (%s, %s, %s, %s, %s, 'default_avatar.png')",
                    (student_num, first_name, last_name, email, p_id)
                )
                imported_count += 1
            except Exception:
                continue

    conn.commit()
    cursor.close()
    conn.close()

    flash(f'Successfully imported {imported_count} students!', 'success' if imported_count > 0 else 'warning')
    return redirect(url_for('students'))



# ---------------------------------------------------------
# SIDEBAR / NAVIGATION ENDPOINT STUBS
# ---------------------------------------------------------





# ---------------------------------------------------------
# NAVIGATION ENDPOINT STUBS (UNIQUE)
# ---------------------------------------------------------

@app.route('/courses')
@login_required
def courses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM courses")
    courses_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('courses.html', courses=courses_list) if os.path.exists('templates/courses.html') else redirect(url_for('students'))






@app.route('/course/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
def course_edit(course_id):
    if request.method == 'POST':
        flash('Course update feature ready.', 'info')
        return redirect(url_for('courses'))
    return redirect(url_for('courses'))



@app.route('/course/delete/<int:course_id>', methods=['POST'])
@login_required
def course_delete(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        conn.commit()
        log_action('DELETE_COURSE', f"Deleted course ID {course_id}")
        flash('Course deleted successfully.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Cannot delete course: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('courses'))






@app.route('/course_offerings')
@app.route('/offerings')
@login_required
def course_offerings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT co.*, c.course_code, c.units 
        FROM course_offerings co 
        JOIN courses c ON co.course_id = c.course_id
        ORDER BY co.offering_id DESC
    """)
    offerings_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('course_offerings.html', offerings=offerings_list)



@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM courses")
    total_courses = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM enrollments")
    total_enrollments = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM programs")
    total_programs = cursor.fetchone()['total']

    cursor.execute("SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT 5")
    recent_logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        total_programs=total_programs,
        recent_logs=recent_logs
    )



# ---------------------------------------------------------
# LAB 20: STUDENT ENROLLMENT ENGINE
# ---------------------------------------------------------








@app.route('/drop_enrollment/<int:enrollment_id>/<int:student_id>', methods=['POST'])
@login_required
def drop_enrollment(enrollment_id, student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        conn.commit()
        flash('Course enrollment successfully dropped.', 'success')
    except Exception as err:
        conn.rollback()
        flash(f'Failed to drop course: {err}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('student_enrollment', student_id=student_id))



















@app.route('/student_enrollment/<int:student_id>', methods=['GET', 'POST'], endpoint='student_enrollment')
@app.route('/student/<int:student_id>/enrollment', methods=['GET', 'POST'], endpoint='student_enrollment_alt')
@login_required
def student_enrollment(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    if request.method == 'POST':
        selected_id = request.form.get('offering_id') or request.form.get('course_id')
        if not selected_id:
            flash('Please select a valid course offering.', 'warning')
        else:
            try:
                cursor.execute('INSERT INTO enrollments (student_id, offering_id) VALUES (%s, %s)', (student_id, selected_id))
                conn.commit()
                flash('Successfully enrolled student!', 'success')
            except Exception as err:
                conn.rollback()
                flash(f'Enrollment failed: {err}', 'danger')
        return redirect(url_for('student_enrollment', student_id=student_id))

    cursor.execute("""
        SELECT e.*, c.course_code, c.course_code AS course_name, c.units,
               'Sec 1' AS section, '1st Sem' AS semester, '2026-2027' AS academic_year
        FROM enrollments e
        JOIN course_offerings co ON e.offering_id = co.offering_id
        JOIN courses c ON co.course_id = c.course_id
        WHERE e.student_id = %s
    """, (student_id,))
    enrolled_courses = cursor.fetchall()

    cursor.execute("""
        SELECT co.offering_id, co.course_id, c.course_code, c.course_code AS course_name, c.units,
               'Sec 1' AS section, '1st Sem' AS semester, '2026-2027' AS academic_year
        FROM course_offerings co
        JOIN courses c ON co.course_id = c.course_id
        WHERE co.offering_id NOT IN (
            SELECT COALESCE(offering_id, 0) FROM enrollments WHERE student_id = %s
        )
    """, (student_id,))
    available_offerings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'student_enrollment.html',
        student=student,
        enrolled_courses=enrolled_courses,
        enrolled=enrolled_courses,
        available_offerings=available_offerings,
        available=available_offerings
    )








@app.route('/course/new', methods=['GET', 'POST'])
@login_required
def course_new():
    if request.method == 'POST':
        code = request.form.get('course_code') or request.form.get('code', '')
        title = request.form.get('course_title') or request.form.get('course_name') or request.form.get('course_description') or request.form.get('title', '')
        units = request.form.get('units') or 3
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO courses (course_code, course_title, units) VALUES (%s, %s, %s)",
                (code, title, units)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Course added successfully!', 'success')
        except Exception as err:
            flash(f'Failed to add course: {err}', 'danger')
        return redirect(url_for('courses'))

    return render_template('course_form.html') if os.path.exists('templates/course_form.html') else redirect(url_for('courses'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)