from flask import Blueprint, current_app, make_response, render_template, request, url_for
from database.database import get_db

seo_bp = Blueprint("seo", __name__)


def public_vacancy_query():
    return """SELECT v.id,v.title,v.vacancy_type,v.description,v.location,v.salary,v.skills,
    v.eligibility,v.deadline,v.created_at,v.employer_id,ep.organization_name,
    ep.organization_type,ep.website,ep.location AS employer_location
    FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id
    WHERE v.status='active' AND v.moderation_status='approved'
    AND ep.account_status='active'
    AND (v.deadline IS NULL OR v.deadline>=date('now','localtime'))"""


def canonical_base():
    return current_app.config.get("SEO_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/")


@seo_bp.get("/jobs")
def public_jobs():
    q=request.args.get("q","").strip()[:100]
    location=request.args.get("location","").strip()[:100]
    kind=request.args.get("type","").strip()
    page=max(1,request.args.get("page",1,type=int) or 1)
    size=20
    sql=public_vacancy_query()
    args=[]
    if q:
        sql += " AND (v.title LIKE ? OR ep.organization_name LIKE ? OR v.skills LIKE ?)"
        args += [f"%{q}%"]*3
    if location:
        sql += " AND v.location LIKE ?"
        args.append(f"%{location}%")
    if kind in {"Internship","Entry-level Job"}:
        sql += " AND v.vacancy_type=?"
        args.append(kind)
    total=get_db().execute("SELECT COUNT(*) FROM ("+sql+")",args).fetchone()[0]
    jobs=get_db().execute(sql+" ORDER BY v.created_at DESC,v.id DESC LIMIT ? OFFSET ?",[*args,size,(page-1)*size]).fetchall()
    return render_template("public_jobs.html",jobs=jobs,q=q,location=location,kind=kind,page=page,total=total,has_next=page*size<total)


@seo_bp.get("/jobs/<int:vacancy_id>")
def public_job_detail(vacancy_id):
    job=get_db().execute(public_vacancy_query()+" AND v.id=?",(vacancy_id,)).fetchone()
    if not job:
        return render_template("404.html"),404
    schema={"@context":"https://schema.org","@type":"JobPosting","title":job["title"],
      "description":job["description"],"datePosted":(job["created_at"] or "").replace(" ","T"),
      "hiringOrganization":{"@type":"Organization","name":job["organization_name"]},
      "employmentType":"INTERN" if job["vacancy_type"]=="Internship" else "FULL_TIME",
      "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":job["location"]}},
      "identifier":{"@type":"PropertyValue","name":"FresherFlow","value":str(job["id"])}}
    if job["deadline"]:
        schema["validThrough"]=job["deadline"]+"T23:59:59"
    if job["location"] and "remote" in job["location"].lower():
        schema["jobLocationType"]="TELECOMMUTE"
    return render_template("public_job_detail.html",job=job,job_schema=schema)


@seo_bp.get("/robots.txt")
def robots_txt():
    text="""User-agent: *
Allow: /
Disallow: /student/
Disallow: /employer/
Disallow: /admin
Disallow: /settings
Disallow: /messages
Disallow: /notifications
Disallow: /login
Disallow: /register

Sitemap: {}/sitemap.xml
""".format(canonical_base())
    response=make_response(text)
    response.headers["Content-Type"]="text/plain; charset=utf-8"
    return response


@seo_bp.get("/sitemap.xml")
def sitemap_xml():
    base=canonical_base()
    db=get_db()
    jobs=db.execute("""SELECT v.id FROM vacancies v JOIN employer_profiles ep ON ep.user_id=v.employer_id
      WHERE v.status='active' AND v.moderation_status='approved' AND ep.account_status='active'
      AND (v.deadline IS NULL OR v.deadline>=date('now','localtime')) ORDER BY v.id DESC""").fetchall()
    companies=db.execute("SELECT user_id FROM employer_profiles WHERE account_status='active' ORDER BY organization_name").fetchall()
    urls=[{"loc":base+url_for("index"),"changefreq":"weekly","priority":"1.0"},
          {"loc":base+url_for("seo.public_jobs"),"changefreq":"daily","priority":"0.9"}]
    urls += [{"loc":base+url_for("seo.public_job_detail",vacancy_id=r["id"]),"changefreq":"daily","priority":"0.8"} for r in jobs]
    urls += [{"loc":base+url_for("platform.company",employer_id=r["user_id"]),"changefreq":"monthly","priority":"0.5"} for r in companies]
    response=make_response(render_template("sitemap.xml",urls=urls))
    response.headers["Content-Type"]="application/xml; charset=utf-8"
    response.headers["Cache-Control"]="public, max-age=3600"
    return response
