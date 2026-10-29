import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.database import get_db
from security import client_login_ip_key, client_login_key, clear_login_failures, login_is_locked, record_login_failure

college_bp = Blueprint('college', __name__, url_prefix='/college')


def college_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'college' or not session.get('verifier_id'):
            return redirect(url_for('college.login'))
        verifier = get_db().execute(
            "SELECT cv.id, cv.college_id, cv.name, cv.status, c.status AS college_status "
            "FROM college_verifiers cv JOIN colleges c ON c.id=cv.college_id WHERE cv.id=?",
            (session['verifier_id'],),
        ).fetchone()
        if not verifier or verifier['status'] != 'active' or verifier['college_status'] != 'active' or verifier['college_id'] != session.get('college_id'):
            session.clear()
            flash('This college panel account is inactive. Contact the FresherFlow administrator.', 'error')
            return redirect(url_for('college.login'))
        return view(*args, **kwargs)
    return wrapped


@college_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('role') == 'college' and session.get('verifier_id'):
        return redirect(url_for('college.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        db = get_db()
        login_key = client_login_key(request, 'college', email)
        ip_key = client_login_ip_key(request, 'college')
        if login_is_locked(db, login_key) or login_is_locked(db, ip_key):
            flash('Too many failed attempts. Please try again in a few minutes.', 'error')
            return render_template('college/login.html'), 429
        verifier = db.execute(
            "SELECT cv.*, c.name AS college_name, c.status AS college_status "
            "FROM college_verifiers cv JOIN colleges c ON c.id=cv.college_id WHERE cv.email=?",
            (email,),
        ).fetchone()
        valid = False
        if verifier:
            try:
                valid = check_password_hash(verifier['password_hash'], password)
            except (ValueError, TypeError):
                valid = False
        if valid and verifier['status'] == 'active' and verifier['college_status'] == 'active':
            clear_login_failures(db, login_key)
            session.clear()
            session['role'] = 'college'
            session['verifier_id'] = verifier['id']
            session['college_id'] = verifier['college_id']
            session['name'] = verifier['name']
            session['college_name'] = verifier['college_name']
            session.permanent = True
            return redirect(url_for('college.dashboard'))
        record_login_failure(db, login_key)
        record_login_failure(db, ip_key, max_failures=20)
        flash('Invalid credentials or inactive college panel.', 'error')
    return render_template('college/login.html')


@college_bp.post('/logout')
@college_required
def logout():
    session.clear()
    flash('You have been signed out of the college panel.', 'success')
    return redirect(url_for('college.login'))


@college_bp.get('/')
@college_required
def dashboard():
    db = get_db()
    college_id = session['college_id']
    status = request.args.get('status', 'pending').strip().lower()
    if status not in {'pending', 'college_approved', 'college_rejected', 'all'}:
        status = 'pending'
    where = 'r.college_id=?'
    params = [college_id]
    if status != 'all':
        where += ' AND r.status=?'
        params.append(status)
    requests = db.execute(
        "SELECT r.*, u.name AS student_name, u.email AS student_email, "
        "sp.college AS profile_college, sp.education "
        "FROM student_verification_requests r "
        "JOIN users u ON u.id=r.student_id "
        "LEFT JOIN student_profiles sp ON sp.user_id=u.id WHERE " + where +
        " ORDER BY CASE r.status WHEN 'pending' THEN 0 ELSE 1 END, r.submitted_at DESC",
        params,
    ).fetchall()
    counts = {
        row['status']: row['total']
        for row in db.execute(
            'SELECT status, COUNT(*) AS total FROM student_verification_requests WHERE college_id=? GROUP BY status',
            (college_id,),
        ).fetchall()
    }
    return render_template('college/dashboard.html', requests=requests, counts=counts, status=status)


@college_bp.route('/students', methods=['GET', 'POST'])
@college_required
def student_accounts():
    db = get_db()
    college_id = session['college_id']
    college = db.execute(
        "SELECT id, name FROM colleges WHERE id=? AND status='active'",
        (college_id,),
    ).fetchone()
    if not college:
        session.clear()
        flash('This college panel account is inactive. Contact the FresherFlow administrator.', 'error')
        return redirect(url_for('college.login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        enrollment_number = request.form.get('enrollment_number', '').strip()
        graduation_year = request.form.get('graduation_year', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if (
            not name
            or len(name) > 120
            or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email)
            or len(email) > 254
            or not enrollment_number
            or len(enrollment_number) > 80
            or not graduation_year.isdigit()
            or not 2000 <= int(graduation_year) <= 2100
        ):
            flash('Enter a valid student name, email, enrollment number and graduation year.', 'error')
            return redirect(url_for('college.student_accounts'))
        if len(password) < 12 or password != confirm_password:
            flash('Use a password of at least 12 characters and confirm it correctly.', 'error')
            return redirect(url_for('college.student_accounts'))

        try:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone():
                db.rollback()
                flash('That email is already registered. Use a different student email.', 'error')
                return redirect(url_for('college.student_accounts'))
            if db.execute(
                'SELECT 1 FROM college_student_accounts WHERE college_id=? AND enrollment_number=? COLLATE NOCASE',
                (college_id, enrollment_number),
            ).fetchone():
                db.rollback()
                flash('That enrollment number already exists for your college.', 'error')
                return redirect(url_for('college.student_accounts'))

            cursor = db.execute(
                "INSERT INTO users(name, email, password_hash, role) VALUES(?, ?, ?, 'student')",
                (name, email, generate_password_hash(password)),
            )
            student_id = cursor.lastrowid
            db.execute(
                'INSERT INTO student_profiles(user_id, college, graduation_year) VALUES(?, ?, ?)',
                (student_id, college['name'], graduation_year),
            )
            db.execute(
                'INSERT INTO college_student_accounts '
                '(user_id, college_id, enrollment_number, graduation_year, created_by_verifier_id) '
                'VALUES(?, ?, ?, ?, ?)',
                (student_id, college_id, enrollment_number, graduation_year, session['verifier_id']),
            )
            db.execute(
                "INSERT INTO student_verification_requests "
                "(student_id, college_id, enrollment_number, graduation_year, status, reviewer_id, reviewer_note, reviewed_at, admin_status) "
                "VALUES(?, ?, ?, ?, 'college_approved', ?, ?, CURRENT_TIMESTAMP, 'pending')",
                (
                    student_id,
                    college_id,
                    enrollment_number,
                    graduation_year,
                    session['verifier_id'],
                    'Student account issued by the college; awaiting final Admin review.',
                ),
            )
            db.execute(
                "INSERT INTO audit_log(actor_type, actor_id, action, target_type, target_id, details, ip_address) "
                "VALUES('college', ?, 'create_student_account', 'student_account', ?, ?, ?)",
                (str(session['verifier_id']), str(student_id), f'College ID: {college_id}', request.remote_addr),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash('The student email or enrollment number is already in use.', 'error')
            return redirect(url_for('college.student_accounts'))
        except sqlite3.DatabaseError:
            db.rollback()
            current_app.logger.exception('College student account creation failed')
            flash('The student account could not be created. Please try again.', 'error')
            return redirect(url_for('college.student_accounts'))

        flash('Student account created. Share the login email and initial password securely.', 'success')
        return redirect(url_for('college.student_accounts'))

    students = db.execute(
        "SELECT u.id, u.name, u.email, csa.enrollment_number, csa.graduation_year, csa.created_at "
        "FROM college_student_accounts csa JOIN users u ON u.id=csa.user_id "
        "WHERE csa.college_id=? ORDER BY csa.created_at DESC, u.id DESC",
        (college_id,),
    ).fetchall()
    return render_template('college/students.html', students=students)


@college_bp.post('/requests/<int:request_id>/decision')
@college_required
def decide_request(request_id):
    decision = request.form.get('decision', '').strip().lower()
    note = request.form.get('note', '').strip()[:500] or None
    if decision not in {'college_approved', 'college_rejected'}:
        flash('Choose approve or reject.', 'error')
        return redirect(url_for('college.dashboard'))
    db = get_db()
    try:
        db.execute('BEGIN IMMEDIATE')
        request_row = db.execute(
            'SELECT id, status FROM student_verification_requests WHERE id=? AND college_id=?',
            (request_id, session['college_id']),
        ).fetchone()
        if not request_row:
            db.rollback()
            return render_template('404.html'), 404
        if request_row['status'] != 'pending':
            db.rollback()
            flash('This request has already been reviewed.', 'error')
            return redirect(url_for('college.dashboard'))
        cursor = db.execute(
            """UPDATE student_verification_requests
               SET status=?, reviewer_id=?, reviewer_note=?, reviewed_at=CURRENT_TIMESTAMP
               WHERE id=? AND college_id=? AND status='pending'""",
            (decision, session['verifier_id'], note, request_id, session['college_id']),
        )
        if cursor.rowcount != 1:
            db.rollback()
            flash('This request was already reviewed. Refresh the queue.', 'error')
            return redirect(url_for('college.dashboard'))
        db.execute(
            "INSERT INTO audit_log(actor_type, actor_id, action, target_type, target_id, details, ip_address) "
            "VALUES('college', ?, ?, 'student_verification_request', ?, ?, ?)",
            (str(session['verifier_id']), decision, str(request_id), note, request.remote_addr),
        )
        db.commit()
    except sqlite3.DatabaseError:
        db.rollback()
        flash('The decision could not be saved. Please try again.', 'error')
        return redirect(url_for('college.dashboard'))
    flash('Student request ' + ('approved' if decision == 'college_approved' else 'rejected') + '.', 'success')
    return redirect(url_for('college.dashboard'))


@college_bp.get('/requests/<int:request_id>')
@college_required
def request_detail(request_id):
    item = get_db().execute(
        "SELECT r.*, u.name AS student_name, u.email AS student_email, sp.college AS profile_college, sp.education "
        "FROM student_verification_requests r JOIN users u ON u.id=r.student_id "
        "LEFT JOIN student_profiles sp ON sp.user_id=u.id "
        "WHERE r.id=? AND r.college_id=?",
        (request_id, session['college_id']),
    ).fetchone()
    if not item:
        return render_template('404.html'), 404
    return render_template('college/request_detail.html', item=item)

@college_bp.get('/requests/<int:request_id>/document')
@college_required
def request_document(request_id):
    item = get_db().execute(
        "SELECT supporting_document_filename FROM student_verification_requests "
        "WHERE id=? AND college_id=?",
        (request_id, session['college_id']),
    ).fetchone()
    if not item or not item['supporting_document_filename']:
        return render_template('404.html'), 404
    filename = item['supporting_document_filename']
    response = send_from_directory(
        current_app.config['VERIFICATION_UPLOAD_FOLDER'],
        filename,
        as_attachment=True,
        download_name=f"college-supporting-document{Path(filename).suffix.lower()}",
    )
    response.headers['Cache-Control'] = 'private, no-store'
    return response
