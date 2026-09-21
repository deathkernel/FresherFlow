"""Create the demo employer and 50 vacancies through FresherFlow's HTTP flow.

This intentionally does NOT call database/demo_seed.py or insert vacancies directly.
It uses the same /register, /login, and /employer/vacancies/bulk-new endpoints that
an employer account uses in the application.

Run from the repository root:
    python scripts/post_demo_jobs_via_employer_flow.py
"""

from app import create_app
from database.database import get_db

EMPLOYER = {
    "name": "FresherFlow Demo Employer",
    "email": "employer.demo@fresherflow.local",
    "password": "FresherFlow@123",
    "organization_name": "FresherFlow Demo Technologies",
    "organization_type": "Technology",
    "location": "Pune, Maharashtra",
    "description": "Demo employer account for testing FresherFlow employer workflows.",
}

INTERNSHIPS = [
    "Python Developer Intern",
    "Data Analyst Intern",
    "Cybersecurity Intern",
    "Frontend Developer Intern",
    "Backend Developer Intern",
    "Cloud Engineering Intern",
    "DevOps Intern",
    "QA Automation Intern",
    "Machine Learning Intern",
    "Java Developer Intern",
    "Mobile App Developer Intern",
    "UI/UX Design Intern",
    "Business Analyst Intern",
    "Product Management Intern",
    "Data Engineering Intern",
    "Cloud Applications Intern",
    "Network Security Intern",
    "SOC Analyst Intern",
    "AI Research Intern",
    "Software Testing Intern",
    "SQL Developer Intern",
    "Technical Support Intern",
    "Web Development Intern",
    "Cloud Security Intern",
    "Automation Engineer Intern",
]

JOBS = [
    "Junior Software Engineer",
    "Associate Data Analyst",
    "Cybersecurity Analyst",
    "Frontend Developer",
    "Backend Engineer",
    "Cloud Support Engineer",
    "DevOps Engineer",
    "QA Engineer",
    "Machine Learning Engineer",
    "Java Software Engineer",
    "Flutter Developer",
    "UI/UX Designer",
    "Business Analyst",
    "Associate Product Manager",
    "Data Engineer",
    "Cloud Software Engineer",
    "Security Operations Analyst",
    "Application Security Engineer",
    "AI Engineer",
    "Software Test Engineer",
    "Database Developer",
    "Technical Support Engineer",
    "Full Stack Developer",
    "Cloud Security Engineer",
    "Automation Engineer",
]


def vacancy(title, vacancy_type):
    is_internship = vacancy_type == "Internship"
    return {
        "title": title,
        "vacancy_type": vacancy_type,
        "location": "Pune, Maharashtra",
        "description": (
            f"Work with the FresherFlow Demo Technologies team as a {title}. "
            "Contribute to real-world projects, collaborate with the team, and build practical skills."
        ),
        "salary": "₹15,000–₹25,000/month" if is_internship else "₹4.5–₹8 LPA",
        "skills": (
            "Python, SQL, Git, problem solving"
            if is_internship
            else "Python, SQL, Git, problem solving, communication"
        ),
        "eligibility": (
            "Students and freshers with relevant fundamentals"
            if is_internship
            else "0–2 years / freshers"
        ),
        "deadline": "2027-12-31",
    }


def main():
    if len(INTERNSHIPS) != 25 or len(JOBS) != 25:
        raise RuntimeError("Expected exactly 25 internships and 25 jobs")

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.test_client() as client:
        # Recreate the account through the public registration flow, not a seed.
        with app.app_context():
            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE email=?", (EMPLOYER["email"],)
            ).fetchone()
            if existing:
                db.execute(
                    "DELETE FROM employer_profiles WHERE user_id=?", (existing["id"],)
                )
                db.execute(
                    "DELETE FROM users WHERE id=? AND role='employer'",
                    (existing["id"],),
                )
                db.commit()

        response = client.post(
            "/register",
            data={
                "name": EMPLOYER["name"],
                "email": EMPLOYER["email"],
                "password": EMPLOYER["password"],
                "confirm_password": EMPLOYER["password"],
                "role": "employer",
                "organization_name": EMPLOYER["organization_name"],
                "organization_type": EMPLOYER["organization_type"],
                "location": EMPLOYER["location"],
                "description": EMPLOYER["description"],
            },
            follow_redirects=False,
        )
        if response.status_code not in (302, 303):
            raise RuntimeError(
                f"Employer registration failed: HTTP {response.status_code}"
            )

        # Log in exactly as the employer would.
        response = client.post(
            "/login?role=employer",
            data={"email": EMPLOYER["email"], "password": EMPLOYER["password"]},
            follow_redirects=False,
        )
        if response.status_code not in (
            302,
            303,
        ) or "/employer/dashboard" not in response.headers.get("Location", ""):
            raise RuntimeError(f"Employer login failed: HTTP {response.status_code}")

        vacancies = [vacancy(t, "Internship") for t in INTERNSHIPS]
        vacancies += [vacancy(t, "Entry-level Job") for t in JOBS]

        # Submit through the employer bulk-post endpoint. No direct vacancy INSERT is used here.
        form = []
        for item in vacancies:
            for key in (
                "title",
                "vacancy_type",
                "location",
                "description",
                "salary",
                "skills",
                "eligibility",
                "deadline",
            ):
                form.append((key, item[key]))

        response = client.post(
            "/employer/vacancies/bulk-new", data=form, follow_redirects=False
        )
        if response.status_code not in (302, 303):
            raise RuntimeError(
                f"Bulk employer posting failed: HTTP {response.status_code}"
            )

        with app.app_context():
            db = get_db()
            user = db.execute(
                "SELECT id, role FROM users WHERE email=?", (EMPLOYER["email"],)
            ).fetchone()
            count = db.execute(
                "SELECT COUNT(*) AS c FROM vacancies WHERE employer_id=?", (user["id"],)
            ).fetchone()["c"]
            internships = db.execute(
                "SELECT COUNT(*) AS c FROM vacancies WHERE employer_id=? AND vacancy_type='Internship'",
                (user["id"],),
            ).fetchone()["c"]
            jobs = db.execute(
                "SELECT COUNT(*) AS c FROM vacancies WHERE employer_id=? AND vacancy_type='Entry-level Job'",
                (user["id"],),
            ).fetchone()["c"]
            if (
                user["role"] != "employer"
                or count != 50
                or internships != 25
                or jobs != 25
            ):
                raise RuntimeError(
                    f"Verification failed: total={count}, internships={internships}, jobs={jobs}"
                )

    print(
        "Created through employer flow: 25 internships + 25 entry-level jobs = 50 vacancies."
    )
    print(f"Employer ID: {EMPLOYER['email']}")
    print(f"Password: {EMPLOYER['password']}")


if __name__ == "__main__":
    main()
