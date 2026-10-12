from werkzeug.security import check_password_hash

from database.database import get_db


def test_settings_preferences_persist_and_are_role_protected(app):
    from tests.test_workflows import seed_student, login, csrf

    seed_student(app)
    client = app.test_client()
    login(client, "student", "student@example.com", "student-password-123")
    token = csrf(client, "/settings")
    response = client.post("/settings", data={
        "csrf_token": token, "theme": "dark", "font_scale": "large",
        "reduce_motion": "on", "notify_application": "on",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your preferences have been saved." in response.data
    with app.app_context():
        row = get_db().execute(
            "SELECT theme,font_scale,reduce_motion,notify_application,notify_message "
            "FROM user_preferences WHERE user_id=(SELECT id FROM users WHERE email=?)",
            ("student@example.com",),
        ).fetchone()
        assert tuple(row) == ("dark", "large", 1, 1, 0)


def test_settings_requires_authentication(app):
    response = app.test_client().get("/settings")
    assert response.status_code == 302
