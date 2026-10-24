import os
from flask import Flask, flash, redirect, render_template, request, url_for
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for flash messages


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "admin1234"),
        database=os.getenv("DB_NAME", "enrollment_system_db"),
        port=int(os.getenv("DB_PORT", 3306)),
    )


# ---------------------------------------------------------
# STUDENT ROUTES
# ---------------------------------------------------------
@app.route("/")
@app.route("/students")
def students():
    q = request.args.get("q", "")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if q:
        query = """
            SELECT s.*, p.program_code 
            FROM students s 
            LEFT JOIN programs p ON s.program_id = p.program_id
            WHERE s.first_name LIKE %s OR s.last_name LIKE %s OR s.student_number LIKE %s OR s.email LIKE %s
        """
        like_q = f"%{q}%"
        cursor.execute(query, (like_q, like_q, like_q, like_q))
    else:
        cursor.execute("""
            SELECT s.*, p.program_code 
            FROM students s 
            LEFT JOIN programs p ON s.program_id = p.program_id
        """)

    students_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("students.html", students=students_list, q=q)


@app.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM programs")
    programs = cursor.fetchall()

    if request.method == "POST":
        student_number = request.form.get("student_number")
        program_id = request.form.get("program_id") or None
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name")
        last_name = request.form.get("last_name")
        birthdate = request.form.get("birthdate") or None
        email = request.form.get("email")
        contact_number = request.form.get("contact_number")
        address = request.form.get("address")

        try:
            cursor.execute(
                """
                INSERT INTO students (student_number, program_id, first_name, middle_name, 
                                    last_name, birthdate, email, contact_number, address, year_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """,
                (
                    student_number,
                    program_id,
                    first_name,
                    middle_name,
                    last_name,
                    birthdate,
                    email,
                    contact_number,
                    address,
                ),
            )
            conn.commit()
            flash("Student successfully registered!", "success")
            return redirect(url_for("students"))
        except Exception as e:
            flash(f"Error: {e}", "error")
            return render_template(
                "register.html",
                form=request.form,
                programs=programs,
                errors=[str(e)],
            )
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html", form={}, programs=programs)


@app.route("/student/<int:student_id>")
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
        flash("Student not found", "error")
        return redirect(url_for("students"))

    return render_template(
        "student_profile.html",
        student=student,
        updated=request.args.get("updated"),
    )


@app.route("/student/<int:student_id>/edit", methods=["GET", "POST"])
def student_edit(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM programs")
    programs = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM students WHERE student_id = %s", (student_id,)
    )
    student = cursor.fetchone()

    if request.method == "POST":
        year_level = request.form.get("year_level")
        program_id = request.form.get("program_id") or None
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name")
        last_name = request.form.get("last_name")
        birthdate = request.form.get("birthdate") or None
        email = request.form.get("email")
        contact_number = request.form.get("contact_number")
        address = request.form.get("address")

        try:
            cursor.execute(
                """
                UPDATE students 
                SET year_level=%s, program_id=%s, first_name=%s, middle_name=%s, 
                    last_name=%s, birthdate=%s, email=%s, contact_number=%s, address=%s
                WHERE student_id=%s
            """,
                (
                    year_level,
                    program_id,
                    first_name,
                    middle_name,
                    last_name,
                    birthdate,
                    email,
                    contact_number,
                    address,
                    student_id,
                ),
            )
            conn.commit()
            return redirect(
                url_for("student_profile", student_id=student_id, updated=True)
            )
        except Exception as e:
            flash(f"Error: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        "student_edit.html", student=student, form=student, programs=programs
    )


# ---------------------------------------------------------
# PROGRAM ROUTES
# ---------------------------------------------------------
@app.route("/programs")
def programs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, COUNT(s.student_id) as student_count 
        FROM programs p 
        LEFT JOIN students s ON p.program_id = s.program_id 
        GROUP BY p.program_id
    """)
    programs_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("programs.html", programs=programs_list)


@app.route("/program/new", methods=["GET", "POST"])
def program_new():
    if request.method == "POST":
        program_code = request.form.get("program_code")
        program_name = request.form.get("program_name")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO programs (program_code, program_name) VALUES"
                " (%s, %s)",
                (program_code, program_name),
            )
            conn.commit()
            flash("Program successfully added!", "success")
            return redirect(url_for("programs"))
        except Exception as e:
            flash(f"Error: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("program_form.html", form={})


@app.route("/program/<int:program_id>/edit", methods=["GET", "POST"])
def program_edit(program_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM programs WHERE program_id = %s", (program_id,)
    )
    program = cursor.fetchone()

    if request.method == "POST":
        program_code = request.form.get("program_code")
        program_name = request.form.get("program_name")

        try:
            cursor.execute(
                "UPDATE programs SET program_code=%s, program_name=%s WHERE"
                " program_id=%s",
                (program_code, program_name, program_id),
            )
            conn.commit()
            flash("Program successfully updated!", "success")
            return redirect(url_for("programs"))
        except Exception as e:
            flash(f"Error: {e}", "error")

    cursor.close()
    conn.close()
    return render_template("program_form.html", program=program, form=program)


@app.route("/program/<int:program_id>/delete", methods=["POST"])
def program_delete(program_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM programs WHERE program_id = %s", (program_id,)
        )
        conn.commit()
        flash("Program deleted successfully.", "success")
    except Exception as e:
        flash(
            "Cannot delete program. It may be assigned to existing students.",
            "error",
        )
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("programs"))


# ---------------------------------------------------------
# COURSE MANAGEMENT ROUTES
# ---------------------------------------------------------
@app.route("/courses")
def courses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM courses")
    courses_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("courses.html", courses=courses_list)


@app.route("/course/new", methods=["GET", "POST"])
def course_new():
    if request.method == "POST":
        course_code = request.form.get("course_code")
        course_title = request.form.get("course_title")
        units = request.form.get("units")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO courses (course_code, course_title, units) VALUES"
                " (%s, %s, %s)",
                (course_code, course_title, units),
            )
            conn.commit()
            flash("Course successfully added!", "success")
            return redirect(url_for("courses"))
        except Exception as e:
            flash(f"Error adding course: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("course_form.html", form={})


@app.route("/course/edit/<int:course_id>", methods=["GET", "POST"])
def course_edit(course_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM courses WHERE course_id = %s", (course_id,))
    course_data = cursor.fetchone()

    if request.method == "POST":
        course_code = request.form.get("course_code")
        course_title = request.form.get("course_title")
        units = request.form.get("units")

        try:
            cursor.execute(
                "UPDATE courses SET course_code=%s, course_title=%s, units=%s"
                " WHERE course_id=%s",
                (course_code, course_title, units, course_id),
            )
            conn.commit()
            flash("Course successfully updated!", "success")
            return redirect(url_for("courses"))
        except Exception as e:
            flash(f"Error updating course: {e}", "error")

    cursor.close()
    conn.close()
    return render_template(
        "course_form.html", course=course_data, form=course_data
    )


@app.route("/course/delete/<int:course_id>", methods=["POST"])
def course_delete(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        conn.commit()
        flash("Course deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting course: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("courses"))


# ---------------------------------------------------------
# LAB 8: COURSE OFFERINGS ROUTES
# ---------------------------------------------------------
@app.route("/offerings")
def offerings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.*, c.course_code, c.course_title 
        FROM course_offerings o
        JOIN courses c ON o.course_id = c.course_id
    """)
    offerings_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("offerings.html", offerings=offerings_list)


@app.route("/offering/new", methods=["GET", "POST"])
def offering_new():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == "POST":
        course_id = request.form.get("course_id")
        section_name = request.form.get("section_name")
        schedule = request.form.get("schedule")
        room = request.form.get("room")
        capacity = request.form.get("capacity", 40)

        try:
            cursor.execute(
                """
                INSERT INTO course_offerings (course_id, section_name, schedule, room, capacity)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (course_id, section_name, schedule, room, capacity),
            )
            conn.commit()
            flash("Course offering created successfully!", "success")
            return redirect(url_for("offerings"))
        except Exception as e:
            flash(f"Error creating offering: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("offering_form.html", courses=courses, form={})


@app.route("/offering/delete/<int:offering_id>", methods=["POST"])
def offering_delete(offering_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM course_offerings WHERE offering_id = %s", (offering_id,)
        )
        conn.commit()
        flash("Offering deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting offering: {e}", "error")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("offerings"))


# ---------------------------------------------------------
# LAB 9: ENROLLMENT & ASSESSMENT ROUTES
# ---------------------------------------------------------
@app.route("/student/<int:student_id>/enroll", methods=["GET", "POST"])
def student_enroll(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch student details
    cursor.execute(
        "SELECT * FROM students WHERE student_id = %s", (student_id,)
    )
    student = cursor.fetchone()

    if request.method == "POST":
        selected_offerings = request.form.getlist("offering_ids")

        if not selected_offerings:
            flash("Please select at least one course section to enroll.", "error")
            cursor.close()
            conn.close()
            return redirect(url_for("student_enroll", student_id=student_id))

        try:
            # Create main enrollment record
            cursor.execute(
                "INSERT INTO enrollments (student_id) VALUES (%s)", (student_id,)
            )
            enrollment_id = cursor.lastrowid

            # Insert selected class offerings into enrollment_items
            for offering_id in selected_offerings:
                cursor.execute(
                    """
                    INSERT INTO enrollment_items (enrollment_id, offering_id)
                    VALUES (%s, %s)
                """,
                    (enrollment_id, offering_id),
                )

            conn.commit()
            flash("Student successfully enrolled!", "success")
            return redirect(url_for("assessment", enrollment_id=enrollment_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error during enrollment: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    # Get available course offerings
    cursor.execute("""
        SELECT co.*, c.course_code, c.course_title, c.units 
        FROM course_offerings co
        JOIN courses c ON co.course_id = c.course_id
    """)
    offerings_list = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template(
        "enrollment_form.html", student=student, offerings=offerings_list
    )


@app.route("/assessment/<int:enrollment_id>")
def assessment(enrollment_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch enrollment and student info
    cursor.execute(
        """
        SELECT e.*, s.student_number, s.first_name, s.last_name, s.email, p.program_name
        FROM enrollments e
        JOIN students s ON e.student_id = s.student_id
        LEFT JOIN programs p ON s.program_id = p.program_id
        WHERE e.enrollment_id = %s
    """,
        (enrollment_id,),
    )
    enrollment = cursor.fetchone()

    # Fetch enrolled course details
    cursor.execute(
        """
        SELECT ei.*, co.section_name, co.schedule, co.room, c.course_code, c.course_title, c.units
        FROM enrollment_items ei
        JOIN course_offerings co ON ei.offering_id = co.offering_id
        JOIN courses c ON co.course_id = c.course_id
        WHERE ei.enrollment_id = %s
    """,
        (enrollment_id,),
    )
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    # Fee Calculations
    total_units = sum(item["units"] for item in items)
    cost_per_unit = 500
    tuition_fee = total_units * cost_per_unit
    miscellaneous_fee = 1500
    grand_total = tuition_fee + miscellaneous_fee

    return render_template(
        "assessment.html",
        enrollment=enrollment,
        items=items,
        total_units=total_units,
        tuition_fee=tuition_fee,
        miscellaneous_fee=miscellaneous_fee,
        grand_total=grand_total,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)