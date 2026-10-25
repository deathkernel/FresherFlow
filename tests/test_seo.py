import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from config import Config
from database.database import get_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(Config,"DATABASE",str(tmp_path/"fresherflow.db"))
    monkeypatch.setattr(Config,"UPLOAD_FOLDER",str(tmp_path/"uploads"))
    monkeypatch.setattr(Config,"SEO_BASE_URL","https://fresherflow.example")
    application=create_app()
    application.config.update(TESTING=True)
    return application


def seed_job(app, *, status="active", moderation="approved", deadline=None, verification="verified"):
    with app.app_context():
        db=get_db()
        email=f"seo-{db.execute('SELECT COUNT(*) FROM users').fetchone()[0]}@example.com"
        eid=db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
          ("SEO Employer",email,generate_password_hash("seo-employer-password-123"),"employer")).lastrowid
        db.execute("""INSERT INTO employer_profiles(company_id,user_id,organization_name,account_status,verification_status,location,description)
          VALUES(?,?,?,?,?,?,?)""",(f"FF-CMP-{eid:06d}",eid,"SEO Company","active",verification,"Pune","Hiring fresh graduates."))
        jid=db.execute("""INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,skills,deadline,status,moderation_status)
          VALUES(?,?,?,?,?,?,?,?,?)""",(eid,"Junior Python Developer","Entry-level Job","Build applications with Python and Flask.","Pune","Python, Flask",deadline,status,moderation)).lastrowid
        db.commit()
        return jid


def test_public_job_pages_are_accessible_and_have_metadata(app):
    jid=seed_job(app)
    client=app.test_client()
    listing=client.get("/jobs")
    detail=client.get(f"/jobs/{jid}")
    assert listing.status_code==200 and b"Junior Python Developer" in listing.data
    assert detail.status_code==200 and b"JobPosting" in detail.data
    assert b'rel="canonical"' in detail.data
    assert b'<meta name="robots" content="noindex, nofollow">' not in detail.data


def test_listing_excludes_unapproved_closed_and_expired_jobs(app):
    seed_job(app)
    seed_job(app,moderation="pending")
    seed_job(app,status="closed")
    seed_job(app,deadline="2000-01-01")
    response=app.test_client().get("/jobs")
    assert response.status_code==200
    assert response.data.count(b"Junior Python Developer")==1


def test_sitemap_uses_configured_domain_and_only_lists_public_jobs(app):
    jid=seed_job(app)
    pending_id=seed_job(app,moderation="pending")
    response=app.test_client().get("/sitemap.xml")
    content=response.get_data(as_text=True)
    assert response.status_code==200 and response.mimetype=="application/xml"
    assert "https://fresherflow.example/jobs" in content
    assert f"https://fresherflow.example/jobs/{jid}" in content
    assert f"https://fresherflow.example/jobs/{pending_id}" not in content
    assert content.count("<url>")==5


def test_robots_txt_excludes_private_workspaces_and_links_sitemap(app):
    response=app.test_client().get("/robots.txt")
    content=response.get_data(as_text=True)
    assert response.status_code==200 and response.mimetype=="text/plain"
    assert "Sitemap: https://fresherflow.example/sitemap.xml" in content
    assert "Disallow: /student/" in content and "Disallow: /settings" in content


def test_private_login_page_is_noindex(app):
    response=app.test_client().get("/login")
    assert response.status_code==200
    assert b'<meta name="robots" content="noindex, nofollow">' in response.data


def test_company_page_job_links_use_public_job_detail(app):
    jid = seed_job(app)
    with app.app_context():
        employer_id = get_db().execute(
            "SELECT employer_id FROM vacancies WHERE id=?", (jid,)
        ).fetchone()["employer_id"]

    response = app.test_client().get(f"/company/{employer_id}")
    assert response.status_code == 200
    assert f'href="/jobs/{jid}"'.encode() in response.data
    assert f'href="/student/jobs/{jid}"'.encode() not in response.data


def test_public_pages_exclude_unverified_employers(app):
    jid = seed_job(app, verification="pending")
    client = app.test_client()

    listing = client.get("/jobs")
    detail = client.get(f"/jobs/{jid}")
    sitemap = client.get("/sitemap.xml")
    company = client.get(f"/company/1")

    assert listing.status_code == 200
    assert b"Junior Python Developer" not in listing.data
    assert detail.status_code == 404
    assert f"https://fresherflow.example/jobs/{jid}".encode() not in sitemap.data
    assert company.status_code == 404
