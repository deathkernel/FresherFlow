import io
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

from app import create_app
from config import Config
from database.database import get_db


def csrf(client, path):
    client.get(path)
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_college_approval_workflow_and_login(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(Config, "VERIFICATION_UPLOAD_FOLDER", str(tmp_path / "verification-documents"))
    admin_password = "admin-test-password-123"
    college_password = "college-test-password-123"
    student_password = "student-test-password-123"
    monkeypatch.setenv("FRESHERFLOW_ENV", "development")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", generate_password_hash(admin_password))

    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    # The platform admin provisions the college verifier account.
    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "email": "admin@example.com", "password": admin_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    token = csrf(client, "/admin/colleges/")
    response = client.post(
        "/admin/colleges/",
        data={
            "csrf_token": token,
            "college_name": "Example Technical College",
            "verifier_name": "College Reviewer",
            "email": "reviewer@example.edu",
            "password": college_password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Create a student using the same schema and authentication rules as the app.
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'student')",
            ("Test Student", "student@example.com", generate_password_hash(student_password)),
        )
        student_id = db.execute(
            "SELECT id FROM users WHERE email='student@example.com'"
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO student_profiles(user_id,college,education) VALUES(?,?,?)",
            (student_id, "Example Technical College", "B.Tech"),
        )
        db.commit()

    token = csrf(client, "/login?role=student")
    response = client.post(
        "/login?role=student",
        data={"csrf_token": token, "email": "student@example.com", "password": student_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    token = csrf(client, "/student/verification")
    invalid_response = client.post(
        "/student/verification",
        data={
            "csrf_token": token,
            "college_id": "1",
            "enrollment_number": "ETC-2024-101",
            "graduation_year": "2027",
            "supporting_document": (io.BytesIO(b"not a PDF"), "student-id.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert invalid_response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM student_verification_requests"
        ).fetchone()[0] == 0

    token = csrf(client, "/student/verification")
    response = client.post(
        "/student/verification",
        data={
            "csrf_token": token,
            "college_id": "1",
            "enrollment_number": "ETC-2024-101",
            "graduation_year": "2027",
            "supporting_document": (
                io.BytesIO(b"%PDF-1.4\\nFresherFlow test document"),
                "student-id.pdf",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        row = get_db().execute(
            "SELECT supporting_document_filename FROM student_verification_requests "
            "WHERE student_id=?",
            (student_id,),
        ).fetchone()
        assert row["supporting_document_filename"]
        assert (Path(Config.VERIFICATION_UPLOAD_FOLDER) / row["supporting_document_filename"]).is_file()
    student_document = client.get("/student/verification/document")
    assert student_document.status_code == 200
    assert b"%PDF-1.4" in student_document.data
    assert student_document.headers["Cache-Control"] == "private, no-store"

    # The college login can see and approve its own queue.
    client.post(
        "/logout",
        data={"csrf_token": csrf(client, "/login?role=student")},
        follow_redirects=False,
    )
    token = csrf(client, "/college/login")
    response = client.post(
        "/college/login",
        data={"csrf_token": token, "email": "reviewer@example.edu", "password": college_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    dashboard = client.get("/college/")
    assert dashboard.status_code == 200
    assert b"ETC-2024-101" in dashboard.data

    college_document = client.get("/college/requests/1/document")
    assert college_document.status_code == 200
    assert b"%PDF-1.4" in college_document.data

    token = csrf(client, "/college/requests/1")
    response = client.post(
        "/college/requests/1/decision",
        data={
            "csrf_token": token,
            "decision": "college_approved",
            "note": "Enrollment confirmed in college records.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        request_row = get_db().execute(
            "SELECT status, reviewer_note FROM student_verification_requests WHERE student_id=?",
            (student_id,),
        ).fetchone()
        assert request_row["status"] == "college_approved"
        assert request_row["reviewer_note"] == "Enrollment confirmed in college records."

    # Final platform-admin review is separate from the college's decision.
    token = csrf(client, "/college/login")
    client.post("/college/logout", data={"csrf_token": token}, follow_redirects=False)
    token = csrf(client, "/admin/login")
    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "email": "admin@example.com", "password": admin_password},
        follow_redirects=False,
    )
    assert response.status_code == 302

    queue = client.get("/admin/student-verifications")
    assert queue.status_code == 200
    assert b"ETC-2024-101" in queue.data
    admin_document = client.get("/admin/student-verifications/1/document")
    assert admin_document.status_code == 200
    assert b"%PDF-1.4" in admin_document.data
    token = csrf(client, "/admin/student-verifications")
    response = client.post(
        "/admin/student-verifications/1/decision",
        data={"csrf_token": token, "decision": "verified", "note": "Records checked."},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        request_row = get_db().execute(
            "SELECT status, admin_status, admin_review_note FROM student_verification_requests WHERE student_id=?",
            (student_id,),
        ).fetchone()
        assert request_row["status"] == "college_approved"
        assert request_row["admin_status"] == "verified"
        assert request_row["admin_review_note"] == "Records checked."

    # A second final decision must not overwrite the first one.
    token = csrf(client, "/admin/student-verifications")
    response = client.post(
        "/admin/student-verifications/1/decision",
        data={"csrf_token": token, "decision": "rejected", "note": "Conflicting retry"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT admin_status FROM student_verification_requests WHERE student_id=?",
            (student_id,),
        ).fetchone()["admin_status"] == "verified"
        get_db().execute(
            "UPDATE student_verification_requests SET expires_at=? WHERE student_id=?",
            ((date.today() - timedelta(days=1)).isoformat(), student_id),
        )
        get_db().commit()

    # An expired verification can be submitted again for college and admin review.
    token = csrf(client, "/admin/login")
    client.post("/admin/logout", data={"csrf_token": token}, follow_redirects=False)
    token = csrf(client, "/login?role=student")
    response = client.post(
        "/login?role=student",
        data={"csrf_token": token, "email": "student@example.com", "password": student_password},
        follow_redirects=False,
    )
    assert response.status_code == 302
    expired_page = client.get("/student/verification")
    assert expired_page.status_code == 200
    assert b"expired" in expired_page.data.lower()
    token = csrf(client, "/student/verification")
    response = client.post(
        "/student/verification",
        data={
            "csrf_token": token,
            "college_id": "1",
            "enrollment_number": "ETC-2024-101",
            "graduation_year": "2027",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        request_row = get_db().execute(
            "SELECT status, admin_status, expires_at FROM student_verification_requests "
            "WHERE student_id=?",
            (student_id,),
        ).fetchone()
        assert request_row["status"] == "pending"
        assert request_row["admin_status"] == "pending"
        assert request_row["expires_at"] is None


def test_college_panel_does_not_allow_unauthenticated_queue_access(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    monkeypatch.setattr(Config, "VERIFICATION_UPLOAD_FOLDER", str(tmp_path / "verification-documents"))
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/college/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/college/login")
