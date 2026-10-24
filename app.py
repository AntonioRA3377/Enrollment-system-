import mysql.connector
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# ---------------------------------------------------------
# DATABASE CONFIGURATION
# ---------------------------------------------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin1234',
    'database': 'enrollment_system_db',
    'port': 3306,
}


def get_db_connection():
    return mysql.connector.connect(**db_config)


# ---------------------------------------------------------
# DASHBOARD ROUTE
# ---------------------------------------------------------
@app.route('/')
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM programs")
    total_programs = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM courses")
    total_courses = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM enrollments")
    total_enrollments = cursor.fetchone()['total']

    cursor.execute("SELECT IFNULL(SUM(amount), 0) AS total FROM payments")
    total_revenue = cursor.fetchone()['total']

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_programs=total_programs,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        total_revenue=total_revenue,
    )


# ---------------------------------------------------------
# STUDENTS ROUTES
# ---------------------------------------------------------
@app.route('/students')
def students():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = request.args.get('q', '').strip()
    if query:
        search_term = f"%{query}%"
        cursor.execute(
            """
            SELECT s.*, p.program_name, p.program_code 
            FROM students s 
            LEFT JOIN programs p ON s.program_id = p.program_id
            WHERE s.first_name LIKE %s OR s.last_name LIKE %s 
               OR s.student_number LIKE %s OR s.email LIKE %s
        """,
            (search_term, search_term, search_term, search_term),
        )
    else:
        cursor.execute("""
            SELECT s.*, p.program_name, p.program_code 
            FROM students s 
            LEFT JOIN programs p ON s.program_id = p.program_id
        """)

    students_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('students.html', students=students_list, q=query)


@app.route('/student/<int:student_id>')
def student_profile(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT s.*, p.program_code, p.program_name 
        FROM students s 
        LEFT JOIN programs p ON s.program_id = p.program_id
        WHERE s.student_id = %s
    """,
        (student_id,),
    )
    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    return render_template('student_profile.html', student=student)


@app.route('/student/new', methods=['GET', 'POST'])
def student_new():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_number = request.form['student_number']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        program_id = request.form.get('program_id')

        try:
            cursor.execute(
                """
                INSERT INTO students (student_number, first_name, last_name, email, program_id)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (student_number, first_name, last_name, email, program_id),
            )
            conn.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            conn.rollback()
            flash(f'Error adding student: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    cursor.execute('SELECT * FROM programs')
    programs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('student_form.html', programs=programs)


@app.route('/student/edit/<int:student_id>', methods=['GET', 'POST'])
def student_edit(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        program_id = request.form.get('program_id')

        try:
            cursor.execute(
                """
                UPDATE students 
                SET first_name = %s, last_name = %s, email = %s, program_id = %s
                WHERE student_id = %s
            """,
                (first_name, last_name, email, program_id, student_id),
            )
            conn.commit()
            flash('Student profile updated successfully!', 'success')
            return redirect(url_for('student_profile', student_id=student_id))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating student: {e}', 'danger')

    cursor.execute('SELECT * FROM students WHERE student_id = %s', (student_id,))
    student = cursor.fetchone()

    cursor.execute('SELECT * FROM programs')
    programs = cursor.fetchall()

    cursor.close()
    conn.close()

    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))

    return render_template('student_form.html', student=student, programs=programs)


@app.route('/student/delete/<int:student_id>', methods=['POST'])
def student_delete(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
        conn.commit()
        flash('Student record deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting student: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('students'))


# ---------------------------------------------------------
# PROGRAMS & COURSES ROUTES
# ---------------------------------------------------------
@app.route('/programs')
def programs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM programs')
    programs_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('programs.html', programs=programs_list)


@app.route('/courses')
def courses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM courses')
    courses_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('courses.html', courses=courses_list)


@app.route('/course/new', methods=['GET', 'POST'])
def course_new():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        course_code = request.form['course_code']
        course_title = request.form['course_title']
        units = request.form['units']

        try:
            cursor.execute(
                """
                INSERT INTO courses (course_code, course_title, units)
                VALUES (%s, %s, %s)
            """,
                (course_code, course_title, units),
            )
            conn.commit()
            flash('Course added successfully!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            conn.rollback()
            flash(f'Error adding course: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('course_form.html')


@app.route('/course/edit/<int:course_id>', methods=['GET', 'POST'])
def course_edit(course_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        course_code = request.form['course_code']
        course_title = request.form['course_title']
        units = request.form['units']

        try:
            cursor.execute(
                """
                UPDATE courses 
                SET course_code = %s, course_title = %s, units = %s 
                WHERE course_id = %s
            """,
                (course_code, course_title, units, course_id),
            )
            conn.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating course: {e}', 'danger')

    cursor.execute('SELECT * FROM courses WHERE course_id = %s', (course_id,))
    course = cursor.fetchone()
    cursor.close()
    conn.close()

    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('courses'))

    return render_template('course_form.html', course=course)


@app.route('/course/delete/<int:course_id>', methods=['POST'])
def course_delete(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        conn.commit()
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting course: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('courses'))


# ---------------------------------------------------------
# LAB 8: COURSE OFFERINGS ROUTES
# ---------------------------------------------------------
@app.route('/offerings')
def offerings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT co.*, c.course_code, c.course_title 
        FROM course_offerings co
        JOIN courses c ON co.course_id = c.course_id
    """)
    offerings_list = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('offerings.html', offerings=offerings_list)


@app.route('/offering/new', methods=['GET', 'POST'])
def offering_new():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        course_id = request.form['course_id']
        section_name = request.form['section_name']
        schedule = request.form['schedule']
        room = request.form['room']
        capacity = request.form['capacity']

        try:
            cursor.execute(
                """
                INSERT INTO course_offerings (course_id, section_name, schedule, room, capacity)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (course_id, section_name, schedule, room, capacity),
            )
            conn.commit()
            flash('Course Offering created successfully!', 'success')
            return redirect(url_for('offerings'))
        except Exception as e:
            conn.rollback()
            flash(f'Error creating offering: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    cursor.execute('SELECT * FROM courses')
    courses_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('offering_form.html', courses=courses_list)


@app.route('/offering/delete/<int:offering_id>', methods=['POST'])
def offering_delete(offering_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM course_offerings WHERE offering_id = %s", (offering_id,))
        conn.commit()
        flash('Course offering deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting offering: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('offerings'))


# ---------------------------------------------------------
# LAB 9 & LAB 11: ENROLLMENT & VALIDATION ROUTES
# ---------------------------------------------------------
@app.route('/enroll/<int:student_id>', methods=['GET', 'POST'])
def enroll(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        selected_offerings = request.form.getlist('offering_ids')

        # 1. Validation: At least one course selected
        if not selected_offerings:
            flash('Please select at least one course to enroll.', 'warning')
            return redirect(url_for('enroll', student_id=student_id))

        try:
            # 2. Validation: Check section capacities & duplicate enrollments
            for offering_id in selected_offerings:
                cursor.execute("""
                    SELECT co.capacity, co.section_name, c.course_code,
                           (SELECT COUNT(*) FROM enrollment_items ei WHERE ei.offering_id = co.offering_id) AS enrolled_count
                    FROM course_offerings co
                    JOIN courses c ON co.course_id = c.course_id
                    WHERE co.offering_id = %s
                """, (offering_id,))
                offering_info = cursor.fetchone()

                if offering_info and offering_info['enrolled_count'] >= offering_info['capacity']:
                    flash(f"Cannot enroll: Course {offering_info['course_code']} ({offering_info['section_name']}) is already full!", "danger")
                    return redirect(url_for('enroll', student_id=student_id))

                cursor.execute("""
                    SELECT ei.item_id 
                    FROM enrollment_items ei
                    JOIN enrollments e ON ei.enrollment_id = e.enrollment_id
                    WHERE e.student_id = %s AND ei.offering_id = %s
                """, (student_id, offering_id))
                already_enrolled = cursor.fetchone()

                if already_enrolled:
                    flash(f"Validation Error: Student is already enrolled in {offering_info['course_code']} ({offering_info['section_name']}).", "danger")
                    return redirect(url_for('enroll', student_id=student_id))

            # 3. Create Enrollment
            cursor.execute("INSERT INTO enrollments (student_id) VALUES (%s)", (student_id,))
            enrollment_id = cursor.lastrowid

            for offering_id in selected_offerings:
                cursor.execute("""
                    INSERT INTO enrollment_items (enrollment_id, offering_id)
                    VALUES (%s, %s)
                """, (enrollment_id, offering_id))

            conn.commit()
            flash('Enrollment successfully validated and created!', 'success')
            return redirect(url_for('assessment', enrollment_id=enrollment_id))

        except Exception as e:
            conn.rollback()
            flash(f'Enrollment validation failed: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    cursor.execute('SELECT * FROM students WHERE student_id = %s', (student_id,))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT co.*, c.course_code, c.course_title, c.units,
               (SELECT COUNT(*) FROM enrollment_items ei WHERE ei.offering_id = co.offering_id) AS enrolled_count
        FROM course_offerings co
        JOIN courses c ON co.course_id = c.course_id
    """)
    available_offerings = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('enrollment_form.html', student=student, offerings=available_offerings)


@app.route('/assessment/<int:enrollment_id>')
def assessment(enrollment_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT e.*, s.first_name, s.last_name, s.student_number, p.program_name
        FROM enrollments e
        JOIN students s ON e.student_id = s.student_id
        LEFT JOIN programs p ON s.program_id = p.program_id
        WHERE e.enrollment_id = %s
    """,
        (enrollment_id,),
    )
    enrollment = cursor.fetchone()

    cursor.execute(
        """
        SELECT co.*, c.course_code, c.course_title, c.units
        FROM enrollment_items ei
        JOIN course_offerings co ON ei.offering_id = co.offering_id
        JOIN courses c ON co.course_id = c.course_id
        WHERE ei.enrollment_id = %s
    """,
        (enrollment_id,),
    )
    enrolled_courses = cursor.fetchall()

    total_units = sum(item['units'] for item in enrolled_courses)
    tuition_fee = total_units * 500
    miscellaneous_fee = 1500
    grand_total = tuition_fee + miscellaneous_fee

    cursor.close()
    conn.close()

    return render_template(
        'assessment.html',
        enrollment=enrollment,
        courses=enrolled_courses,
        total_units=total_units,
        tuition_fee=tuition_fee,
        miscellaneous_fee=miscellaneous_fee,
        grand_total=grand_total,
    )


# ---------------------------------------------------------
# LAB 10: PAYMENT PROCESSING & RECEIPT ROUTES
# ---------------------------------------------------------
@app.route('/payment/new/<int:enrollment_id>', methods=['GET', 'POST'])
def payment_new(enrollment_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT e.*, s.first_name, s.last_name, s.student_number
        FROM enrollments e
        JOIN students s ON e.student_id = s.student_id
        WHERE e.enrollment_id = %s
    """,
        (enrollment_id,),
    )
    enrollment = cursor.fetchone()

    cursor.execute(
        """
        SELECT c.units
        FROM enrollment_items ei
        JOIN course_offerings co ON ei.offering_id = co.offering_id
        JOIN courses c ON co.course_id = c.course_id
        WHERE ei.enrollment_id = %s
    """,
        (enrollment_id,),
    )
    items = cursor.fetchall()

    total_units = sum(item['units'] for item in items) if items else 0
    grand_total = (total_units * 500) + 1500

    if request.method == 'POST':
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        reference_number = request.form.get('reference_number')

        try:
            cursor.execute(
                """
                INSERT INTO payments (enrollment_id, amount, payment_method, reference_number)
                VALUES (%s, %s, %s, %s)
            """,
                (enrollment_id, amount, payment_method, reference_number),
            )

            cursor.execute(
                "UPDATE enrollments SET status = 'Paid' WHERE enrollment_id = %s",
                (enrollment_id,),
            )

            conn.commit()
            payment_id = cursor.lastrowid
            flash('Payment successfully recorded!', 'success')
            return redirect(url_for('receipt', payment_id=payment_id))
        except Exception as e:
            conn.rollback()
            flash(f'Error processing payment: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    cursor.close()
    conn.close()
    return render_template(
        'payment_form.html', enrollment=enrollment, grand_total=grand_total
    )


@app.route('/receipt/<int:payment_id>')
def receipt(payment_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT p.*, e.enrollment_date, s.student_number, s.first_name, s.last_name, pr.program_name
        FROM payments p
        JOIN enrollments e ON p.enrollment_id = e.enrollment_id
        JOIN students s ON e.student_id = s.student_id
        LEFT JOIN programs pr ON s.program_id = pr.program_id
        WHERE p.payment_id = %s
    """,
        (payment_id,),
    )
    payment_data = cursor.fetchone()

    cursor.close()
    conn.close()
    return render_template('receipt.html', payment=payment_data)


# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)