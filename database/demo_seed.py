from werkzeug.security import generate_password_hash

DEMO_EMPLOYER = {
    "name": "FresherFlow Demo Employer",
    "email": "employer.demo@fresherflow.local",
    "password": "FresherFlow@123",
    "organization_name": "FresherFlow Demo Technologies",
    "organization_type": "Technology",
    "location": "Pune, Maharashtra",
}

INTERNSHIPS = [
    (
        "Python Developer Intern",
        "Build backend features and database integrations.",
        "Python, Flask, SQL",
    ),
    (
        "Data Analyst Intern",
        "Prepare datasets, reports and analytical dashboards.",
        "Python, SQL, Excel",
    ),
    (
        "Cybersecurity Intern",
        "Assist with security reviews, logs and vulnerability documentation.",
        "Linux, Networking, Security",
    ),
    (
        "Frontend Developer Intern",
        "Build responsive web interfaces and reusable components.",
        "HTML, CSS, JavaScript",
    ),
    (
        "Backend Developer Intern",
        "Implement APIs and database-backed application features.",
        "Python, APIs, SQL",
    ),
    (
        "Cloud Engineering Intern",
        "Support cloud deployments, monitoring and automation.",
        "AWS, Linux, Git",
    ),
    (
        "DevOps Intern",
        "Assist with CI/CD pipelines and deployment workflows.",
        "Git, Docker, Linux",
    ),
    (
        "QA Automation Intern",
        "Create test cases and automate regression testing.",
        "Python, Selenium, Git",
    ),
    (
        "Machine Learning Intern",
        "Prepare datasets and experiment with machine learning models.",
        "Python, Pandas, scikit-learn",
    ),
    (
        "Java Developer Intern",
        "Work on enterprise Java services and application features.",
        "Java, Spring, SQL",
    ),
    (
        "Mobile App Developer Intern",
        "Build and test cross-platform mobile features.",
        "Flutter, Dart, Git",
    ),
    (
        "UI/UX Design Intern",
        "Create wireframes, user flows and interface designs.",
        "Figma, UX Research, Prototyping",
    ),
    (
        "Business Analyst Intern",
        "Gather requirements and prepare process documentation.",
        "SQL, Excel, Communication",
    ),
    (
        "Product Management Intern",
        "Support product research, planning and user discovery.",
        "Research, Analytics, Communication",
    ),
    (
        "Data Engineering Intern",
        "Help build ETL pipelines and validate data quality.",
        "Python, SQL, ETL",
    ),
    (
        "Cloud Applications Intern",
        "Build and test cloud-native application components.",
        "Python, Docker, Cloud",
    ),
    (
        "Network Security Intern",
        "Assist with network monitoring and security analysis.",
        "Networking, Linux, Security",
    ),
    (
        "SOC Analyst Intern",
        "Review security events and help document incidents.",
        "SIEM, Networking, Linux",
    ),
    (
        "AI Research Intern",
        "Support experiments involving datasets and AI models.",
        "Python, ML, Research",
    ),
    (
        "Software Testing Intern",
        "Design manual and automated test scenarios.",
        "Testing, Python, Git",
    ),
    (
        "SQL Developer Intern",
        "Create queries, reports and database procedures.",
        "SQL, PostgreSQL, Database",
    ),
    (
        "Technical Support Intern",
        "Troubleshoot software and infrastructure issues.",
        "Linux, Networking, Troubleshooting",
    ),
    (
        "Web Development Intern",
        "Develop and maintain full-stack web features.",
        "HTML, CSS, JavaScript, Python",
    ),
    (
        "Cloud Security Intern",
        "Support cloud security reviews and configuration checks.",
        "AWS, IAM, Security",
    ),
    (
        "Automation Engineer Intern",
        "Automate repetitive engineering and operational tasks.",
        "Python, APIs, Automation",
    ),
]

JOBS = [
    (
        "Junior Software Engineer",
        "Develop production software features for web applications.",
        "Python, Git, SQL",
    ),
    (
        "Associate Data Analyst",
        "Create reports, dashboards and actionable data insights.",
        "SQL, Excel, Power BI",
    ),
    (
        "Cybersecurity Analyst",
        "Monitor security events and support vulnerability management.",
        "Networking, Linux, Security Tools",
    ),
    (
        "Frontend Developer",
        "Develop accessible and responsive web applications.",
        "JavaScript, React, CSS",
    ),
    (
        "Backend Engineer",
        "Design APIs and services for scalable applications.",
        "Python, Flask, PostgreSQL",
    ),
    (
        "Cloud Support Engineer",
        "Support cloud workloads and troubleshoot infrastructure.",
        "AWS, Linux, Networking",
    ),
    (
        "DevOps Engineer",
        "Maintain CI/CD pipelines and deployment automation.",
        "Docker, GitHub Actions, Linux",
    ),
    (
        "QA Engineer",
        "Design automated tests and improve software release quality.",
        "Selenium, Python, API Testing",
    ),
    (
        "Machine Learning Engineer",
        "Develop and evaluate machine learning solutions.",
        "Python, ML, Pandas",
    ),
    (
        "Java Software Engineer",
        "Develop and maintain enterprise Java services.",
        "Java, Spring Boot, SQL",
    ),
    (
        "Flutter Developer",
        "Build and maintain cross-platform mobile applications.",
        "Flutter, Dart, REST APIs",
    ),
    (
        "UI/UX Designer",
        "Design product experiences from research through handoff.",
        "Figma, UX, Prototyping",
    ),
    (
        "Business Analyst",
        "Translate business requirements into technical deliverables.",
        "SQL, Excel, Documentation",
    ),
    (
        "Associate Product Manager",
        "Coordinate product discovery, requirements and delivery.",
        "Product, Analytics, Communication",
    ),
    (
        "Data Engineer",
        "Build reliable data pipelines and processing workflows.",
        "Python, SQL, ETL",
    ),
    (
        "Cloud Software Engineer",
        "Develop and operate cloud-native services.",
        "Python, Docker, Kubernetes",
    ),
    (
        "Security Operations Analyst",
        "Investigate alerts and support security operations.",
        "SIEM, Linux, Networking",
    ),
    (
        "Application Security Engineer",
        "Identify and remediate application security issues.",
        "OWASP, Python, Web Security",
    ),
    (
        "AI Engineer",
        "Build software components powered by machine learning models.",
        "Python, ML, APIs",
    ),
    (
        "Software Test Engineer",
        "Plan, automate and maintain software test suites.",
        "Python, Selenium, Testing",
    ),
    (
        "Database Developer",
        "Design queries and maintain application databases.",
        "SQL, PostgreSQL, Database",
    ),
    (
        "Technical Support Engineer",
        "Troubleshoot customer and internal technical issues.",
        "Linux, Networking, Support",
    ),
    (
        "Full Stack Developer",
        "Build end-to-end features across frontend and backend.",
        "JavaScript, Python, SQL",
    ),
    (
        "Cloud Security Engineer",
        "Improve security controls across cloud infrastructure.",
        "AWS, IAM, Cloud Security",
    ),
    (
        "Automation Engineer",
        "Build automation tools and integrations for engineering teams.",
        "Python, APIs, Automation",
    ),
]


def seed_demo_data(db, password=None):
    """Create one demo employer and exactly 50 FresherFlow-native vacancies."""
    login_password = password or DEMO_EMPLOYER["password"]
    password_hash = generate_password_hash(login_password)

    existing = db.execute(
        "SELECT id FROM users WHERE email=?", (DEMO_EMPLOYER["email"],)
    ).fetchone()
    if existing:
        employer_id = existing[0]
        db.execute("DELETE FROM vacancies WHERE employer_id=?", (employer_id,))
        db.execute("DELETE FROM employer_profiles WHERE user_id=?", (employer_id,))
        db.execute("DELETE FROM users WHERE id=?", (employer_id,))

    cur = db.execute(
        "INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'employer')",
        (DEMO_EMPLOYER["name"], DEMO_EMPLOYER["email"], password_hash),
    )
    employer_id = cur.lastrowid

    db.execute(
        "INSERT INTO employer_profiles(user_id,organization_name,organization_type,location,description,account_status,verification_status,verified_at) "
        "VALUES(?,?,?,?,?,'active','verified',CURRENT_TIMESTAMP)",
        (
            employer_id,
            DEMO_EMPLOYER["organization_name"],
            DEMO_EMPLOYER["organization_type"],
            DEMO_EMPLOYER["location"],
            "Demo employer account for testing FresherFlow's student and employer workflows.",
        ),
    )

    for title, description, skills in INTERNSHIPS:
        db.execute(
            "INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status,moderation_status,moderated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?, 'active','approved',CURRENT_TIMESTAMP)",
            (
                employer_id,
                title,
                "Internship",
                description,
                "Pune, Maharashtra",
                "₹15,000–₹25,000/month",
                skills,
                "Students and freshers with relevant fundamentals",
                "2027-12-31",
            ),
        )

    for title, description, skills in JOBS:
        db.execute(
            "INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status,moderation_status,moderated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?, 'active','approved',CURRENT_TIMESTAMP)",
            (
                employer_id,
                title,
                "Entry-level Job",
                description,
                "Pune, Maharashtra",
                "₹4.5–₹8 LPA",
                skills,
                "0–2 years / freshers",
                "2027-12-31",
            ),
        )

    assert len(INTERNSHIPS) == 25
    assert len(JOBS) == 25
    return employer_id
