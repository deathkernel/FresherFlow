from flask import Flask, jsonify, request, render_template_string
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path(__file__).with_name('fresherflow.db')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS opportunities (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 company TEXT NOT NULL,
 type TEXT NOT NULL,
 location TEXT NOT NULL,
 stipend TEXT,
 skills TEXT,
 description TEXT,
 eligibility TEXT
);
CREATE TABLE IF NOT EXISTS applications (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 opportunity_id INTEGER NOT NULL,
 candidate TEXT NOT NULL,
 email TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Applied',
 FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);
'''

SEED = [
 ('Python Developer Intern','TechNova','Internship','Pune, Maharashtra','₹15,000/mo','Python, Flask, SQLite','Build APIs and assist the backend team.','Students / freshers with Python basics'),
 ('Frontend Developer','PixelCraft','Entry-level Job','Remote','₹4.5 LPA','HTML, CSS, JavaScript, Bootstrap','Create responsive user interfaces for client projects.','Freshers with frontend project experience'),
 ('Data Analyst Intern','InsightWorks','Internship','Mumbai, Maharashtra','₹18,000/mo','Python, Excel, SQL','Work with datasets and create business reports.','Students pursuing data or computer-related courses'),
 ('Junior Software Engineer','CodeOrbit','Entry-level Job','Bengaluru, Karnataka','₹6 LPA','Python, Git, SQL','Join the engineering team and ship production features.','0–1 years experience'),
]

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db(); con.executescript(SCHEMA)
    if con.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0] == 0:
        con.executemany('INSERT INTO opportunities(title,company,type,location,stipend,skills,description,eligibility) VALUES (?,?,?,?,?,?,?,?)', SEED)
    con.commit(); con.close()

PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FresherFlow — Launch Your Career</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"><link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"><style>body{font-family:Inter,sans-serif;background:#f7f9fc;color:#172033}.navbar{background:#fff}.brand{font-weight:800;font-size:1.35rem;color:#4f46e5}.hero{background:linear-gradient(135deg,#eef2ff,#fff 60%);padding:72px 0 55px}.hero h1{font-weight:800;font-size:clamp(2.2rem,5vw,4rem);letter-spacing:-.05em}.hero span{color:#4f46e5}.searchbox{background:#fff;border-radius:18px;padding:16px;box-shadow:0 14px 40px #28334d18}.card{border:0;border-radius:18px;box-shadow:0 8px 28px #28334d0d}.badge-soft{background:#eef2ff;color:#4f46e5}.stat{font-weight:800;font-size:1.8rem}.nav-link{font-weight:500}.btn-primary{background:#4f46e5;border-color:#4f46e5}.btn-primary:hover{background:#4338ca;border-color:#4338ca}.section{padding:55px 0}.modal-content{border:0;border-radius:20px}</style></head><body><nav class="navbar navbar-expand-lg border-bottom sticky-top"><div class="container py-2"><a class="navbar-brand brand" href="#">FresherFlow</a><button class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#nav">☰</button><div id="nav" class="collapse navbar-collapse"><div class="navbar-nav ms-auto"><a class="nav-link" href="#opportunities">Find Jobs</a><a class="nav-link" href="#how">How it works</a><button class="btn btn-outline-dark ms-lg-3" data-bs-toggle="modal" data-bs-target="#login">Login</button><button class="btn btn-primary ms-lg-2" data-bs-toggle="modal" data-bs-target="#signup">Create Profile</button></div></div></div></nav><header class="hero"><div class="container"><div class="row align-items-center g-5"><div class="col-lg-7"><span class="badge rounded-pill badge-soft px-3 py-2 mb-3">Built for students & freshers</span><h1>Launch your career with <span>FresherFlow.</span></h1><p class="lead text-secondary mt-3">Find internships and entry-level jobs, build your profile, apply in minutes, and track every application in one place.</p><div class="searchbox mt-4"><div class="row g-2"><div class="col-md-5"><input id="q" class="form-control form-control-lg" placeholder="Job title, skill or company"></div><div class="col-md-4"><select id="type" class="form-select form-select-lg"><option value="">All opportunities</option><option>Internship</option><option>Entry-level Job</option></select></div><div class="col-md-3"><button onclick="loadOpps()" class="btn btn-primary btn-lg w-100">Search</button></div></div></div></div><div class="col-lg-5"><div class="card p-4"><h5 class="fw-bold">Your career dashboard</h5><div class="row text-center mt-3"><div class="col-4"><div class="stat">24</div><small class="text-secondary">Applied</small></div><div class="col-4"><div class="stat">8</div><small class="text-secondary">Shortlisted</small></div><div class="col-4"><div class="stat">2</div><small class="text-secondary">Selected</small></div></div><hr><div class="d-flex justify-content-between"><span>Profile strength</span><b>78%</b></div><div class="progress mt-2" style="height:8px"><div class="progress-bar" style="width:78%"></div></div><p class="small text-secondary mt-3 mb-0">Add your resume and skills to improve your chances.</p></div></div></div></div></header><main><section id="opportunities" class="section"><div class="container"><div class="d-flex justify-content-between align-items-end mb-4"><div><h2 class="fw-bold">Latest opportunities</h2><p class="text-secondary mb-0">Fresh roles matched for early-career candidates.</p></div><span id="count" class="text-secondary"></span></div><div id="list" class="row g-4"></div></div></section><section id="how" class="section bg-white"><div class="container"><div class="text-center mb-5"><h2 class="fw-bold">Everything you need to get hired</h2><p class="text-secondary">One focused platform for the first step of your career.</p></div><div class="row g-4"><div class="col-md-3"><div class="card p-4 h-100"><h4>01</h4><h5>Build profile</h5><p class="text-secondary">Add education, skills, certifications and resume.</p></div></div><div class="col-md-3"><div class="card p-4 h-100"><h4>02</h4><h5>Discover</h5><p class="text-secondary">Search internships and entry-level opportunities.</p></div></div><div class="col-md-3"><div class="card p-4 h-100"><h4>03</h4><h5>Apply</h5><p class="text-secondary">Apply to suitable roles with your profile.</p></div></div><div class="col-md-3"><div class="card p-4 h-100"><h4>04</h4><h5>Track</h5><p class="text-secondary">Follow applications from Applied to Selected.</p></div></div></div></div></section></main><footer class="py-4 bg-dark text-white"><div class="container d-flex justify-content-between"><b>FresherFlow</b><span class="text-white-50">Internship & Job Management System</span></div></footer><div class="modal fade" id="login"><div class="modal-dialog modal-dialog-centered"><div class="modal-content p-4"><h4 class="fw-bold">Welcome back</h4><input class="form-control mt-3" placeholder="Email"><input class="form-control mt-2" type="password" placeholder="Password"><button class="btn btn-primary mt-3" data-bs-dismiss="modal">Login</button></div></div></div><div class="modal fade" id="signup"><div class="modal-dialog modal-dialog-centered"><div class="modal-content p-4"><h4 class="fw-bold">Create your FresherFlow profile</h4><input class="form-control mt-3" placeholder="Full name"><input class="form-control mt-2" placeholder="Email"><select class="form-select mt-2"><option>Student / Fresher</option><option>Employer / Recruiter</option></select><button class="btn btn-primary mt-3" data-bs-dismiss="modal">Create Profile</button></div></div></div><script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script><script>async function loadOpps(){const q=document.getElementById('q').value,type=document.getElementById('type').value;const data=await fetch(`/api/opportunities?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type)}`).then(r=>r.json());document.getElementById('count').textContent=`${data.length} opportunities`;document.getElementById('list').innerHTML=data.map(o=>`<div class="col-md-6"><div class="card p-4 h-100"><div class="d-flex justify-content-between"><span class="badge rounded-pill badge-soft">${o.type}</span><span class="small text-secondary">${o.location}</span></div><h4 class="fw-bold mt-3">${o.title}</h4><p class="mb-1 fw-semibold">${o.company}</p><p class="text-secondary small">${o.description}</p><div class="mb-3">${o.skills.split(',').map(s=>`<span class="badge text-bg-light me-1">${s.trim()}</span>`).join('')}</div><div class="d-flex justify-content-between align-items-center"><span class="small fw-semibold">${o.stipend}</span><button class="btn btn-primary" onclick="apply(${o.id},'${o.title.replace(/'/g,"\\'")}')">Apply now</button></div></div></div>`).join('')}async function apply(id,title){const name=prompt(`Apply for ${title}. Enter your name:`);if(!name)return;const email=prompt('Enter your email:');if(!email)return;const r=await fetch('/api/applications',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({opportunity_id:id,candidate:name,email})});const d=await r.json();alert(d.message)}loadOpps();</script></body></html>'''

@app.get('/')
def home(): return render_template_string(PAGE)

@app.get('/api/opportunities')
def opportunities():
    q=request.args.get('q','').strip(); typ=request.args.get('type','').strip(); con=db()
    sql='SELECT * FROM opportunities WHERE 1=1'; args=[]
    if q: sql += ' AND (title LIKE ? OR company LIKE ? OR skills LIKE ?)'; args += [f'%{q}%']*3
    if typ: sql += ' AND type=?'; args.append(typ)
    rows=con.execute(sql+' ORDER BY id DESC',args).fetchall(); con.close(); return jsonify([dict(r) for r in rows])

@app.post('/api/applications')
def applications():
    data=request.get_json() or {}; con=db()
    if not data.get('opportunity_id') or not data.get('candidate') or not data.get('email'): return jsonify(message='Please provide all details.'),400
    con.execute('INSERT INTO applications(opportunity_id,candidate,email) VALUES(?,?,?)',(data['opportunity_id'],data['candidate'],data['email'])); con.commit(); con.close()
    return jsonify(message='Application submitted successfully! Status: Applied')

@app.get('/api/applications')
def list_applications():
    con=db(); rows=con.execute('SELECT a.*,o.title,o.company FROM applications a JOIN opportunities o ON o.id=a.opportunity_id ORDER BY a.id DESC').fetchall(); con.close(); return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    init_db(); app.run(host='0.0.0.0', port=5000, debug=True)
