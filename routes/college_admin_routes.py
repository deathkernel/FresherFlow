import sqlite3
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from database.database import get_db
from routes.decorators import role_required

college_admin_bp = Blueprint('college_admin', __name__, url_prefix='/admin/colleges')


@college_admin_bp.route('/', methods=['GET', 'POST'])
@role_required('admin')
def manage():
    db = get_db()
    if request.method == 'POST':
        college_name = request.form.get('college_name', '').strip()
        verifier_name = request.form.get('verifier_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not college_name or not verifier_name or not email or len(password) < 12:
            flash('Complete every field. The college password must be at least 12 characters.', 'error')
            return redirect(url_for('college_admin.manage'))
        try:
            db.execute('BEGIN IMMEDIATE')
            college = db.execute('SELECT id, status FROM colleges WHERE name=? COLLATE NOCASE', (college_name,)).fetchone()
            if not college:
                db.execute('INSERT INTO colleges(name) VALUES(?)', (college_name,))
                college = db.execute('SELECT id, status FROM colleges WHERE name=? COLLATE NOCASE', (college_name,)).fetchone()
            if not college or college['status'] != 'active':
                raise ValueError('This college is inactive.')
            db.execute(
                'INSERT INTO college_verifiers(college_id, name, email, password_hash, auth_version) VALUES(?,?,?,?,lower(hex(randomblob(32))))',
                (college['id'], verifier_name, email, generate_password_hash(password)),
            )
            db.execute(
                "INSERT INTO audit_log(actor_type, actor_id, action, target_type, target_id, details, ip_address) VALUES('admin', ?, 'create_college_verifier', 'college', ?, ?, ?)",
                (str(session.get('user_id', 'admin')), str(college['id']), email, request.remote_addr),
            )
            db.commit()
        except ValueError as exc:
            db.rollback()
            flash(str(exc), 'error')
            return redirect(url_for('college_admin.manage'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash('That verifier email is already registered.', 'error')
            return redirect(url_for('college_admin.manage'))
        except sqlite3.DatabaseError:
            db.rollback()
            flash('College account could not be created. Please try again.', 'error')
            return redirect(url_for('college_admin.manage'))
        flash('College panel account created successfully. Share the login details securely.', 'success')
        return redirect(url_for('college_admin.manage'))
    colleges = db.execute(
        "SELECT c.id, c.name, c.status, c.created_at, COUNT(cv.id) AS verifier_count "
        "FROM colleges c LEFT JOIN college_verifiers cv ON cv.college_id=c.id "
        "GROUP BY c.id ORDER BY c.name COLLATE NOCASE",
    ).fetchall()
    return render_template('admin/colleges.html', colleges=colleges)