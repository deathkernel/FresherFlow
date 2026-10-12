from app import create_app
from config import Config
from database.database import get_db


def test_static_assets_have_a_short_browser_cache_lifetime(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()
    app.config.update(TESTING=True)

    response = app.test_client().get("/static/css/style.css")

    assert response.status_code == 200
    assert "max-age=3600" in response.headers.get("Cache-Control", "")


def test_performance_indexes_are_created_and_migration_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATABASE", str(tmp_path / "fresherflow.db"))
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app = create_app()

    with app.app_context():
        db = get_db()
        indexes = {
            row["name"]
            for row in db.execute("PRAGMA index_list(vacancies)").fetchall()
        }
        indexes.update(
            row["name"]
            for row in db.execute("PRAGMA index_list(applications)").fetchall()
        )
        migration_count = db.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version=5"
        ).fetchone()[0]

    assert "idx_vacancies_public_listing" in indexes
    assert "idx_vacancies_public_created" in indexes
    assert "idx_applications_student_applied" in indexes
    assert "idx_applications_vacancy_status" in indexes
    assert migration_count == 1


def test_performance_migration_is_safe_when_app_restarts(tmp_path, monkeypatch):
    database_path = str(tmp_path / "fresherflow.db")
    monkeypatch.setattr(Config, "DATABASE", database_path)
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path / "uploads"))

    create_app()
    app = create_app()

    with app.app_context():
        db = get_db()
        migration_count = db.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version=5"
        ).fetchone()[0]
        indexes = {
            row["name"]
            for row in db.execute("PRAGMA index_list(vacancies)").fetchall()
        }

    assert migration_count == 1
    assert "idx_vacancies_public_listing" in indexes
