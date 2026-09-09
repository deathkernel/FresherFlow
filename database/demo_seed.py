from werkzeug.security import generate_password_hash

COMPANIES = [
    ("AsterByte Technologies","Technology","Pune, Maharashtra"),("BlueOrbit Analytics","Data & Analytics","Mumbai, Maharashtra"),("CloudNest Systems","Cloud Technology","Bengaluru, Karnataka"),("CedarPeak Digital","Digital Services","Hyderabad, Telangana"),("DataMint Labs","Data & Analytics","Pune, Maharashtra"),
    ("ElevateWorks","SaaS","Gurugram, Haryana"),("Finora Technologies","FinTech","Mumbai, Maharashtra"),("GreenGrid Innovations","CleanTech","Ahmedabad, Gujarat"),("HexaBridge Solutions","IT Services","Noida, Uttar Pradesh"),("InnovaCart","E-commerce","Bengaluru, Karnataka"),
    ("JadePeak Software","Technology","Chennai, Tamil Nadu"),("KiteLabs","Developer Tools","Kochi, Kerala"),("Lumina HealthTech","HealthTech","Hyderabad, Telangana"),("MetroMinds Consulting","Consulting","Delhi, Delhi"),("NexaForge","Technology","Pune, Maharashtra"),
    ("OptiRoute Mobility","Mobility","Bengaluru, Karnataka"),("PixelRiver Studios","Media & Design","Mumbai, Maharashtra"),("QuantumLeaf AI","Artificial Intelligence","Bengaluru, Karnataka"),("RiseStack Technologies","Technology","Gurugram, Haryana"),("Skyline Commerce","E-commerce","Jaipur, Rajasthan"),
    ("TerraNova Foods","FoodTech","Indore, Madhya Pradesh"),("UrbanPulse","Smart Cities","Pune, Maharashtra"),("VertexWave","Cybersecurity","Bengaluru, Karnataka"),("Wavefront Robotics","Robotics","Chennai, Tamil Nadu"),("ZenithWorks","Enterprise Technology","Noida, Uttar Pradesh"),
    ("AeroVista Mobility","Mobility","Bengaluru, Karnataka"),("BrightPath Learning","EdTech","Pune, Maharashtra"),("CoreSpring Systems","Technology","Hyderabad, Telangana"),("DeltaScale","Cloud Technology","Mumbai, Maharashtra"),("EchoFrame Media","Media & Design","Mumbai, Maharashtra"),
    ("FusionLedger","FinTech","Gurugram, Haryana"),("GlobeMesh Networks","Networking","Bengaluru, Karnataka"),("HarborStack","Logistics Tech","Chennai, Tamil Nadu"),("IndigoByte","Software","Pune, Maharashtra"),("JuniperWorks","Business Services","Ahmedabad, Gujarat"),
    ("Keystone AI Labs","Artificial Intelligence","Bengaluru, Karnataka"),("Lakeview Digital","Digital Services","Kolkata, West Bengal"),("Moonlit Commerce","E-commerce","Delhi, Delhi"),("NorthStar Systems","Enterprise Technology","Noida, Uttar Pradesh"),("Oakline Tech","Technology","Nagpur, Maharashtra"),
    ("PrimePulse Analytics","Data & Analytics","Mumbai, Maharashtra"),("QuickForge","Developer Tools","Bengaluru, Karnataka"),("Redwood Mobility","Mobility","Pune, Maharashtra"),("SilverArc Technologies","Technology","Hyderabad, Telangana"),("TrueNorth Security","Cybersecurity","Bengaluru, Karnataka"),
    ("UnitySpring Health","HealthTech","Pune, Maharashtra"),("VistaNova Labs","Technology","Chennai, Tamil Nadu"),("WestBridge Solutions","IT Services","Gurugram, Haryana"),("XenoWorks","Technology","Mumbai, Maharashtra"),("YellowTree Innovations","Technology","Ahmedabad, Gujarat")
]

INTERNSHIPS = [
("Python Developer Intern","Build REST APIs and assist the backend engineering team.","Python, Flask, SQL","Students and freshers with Python basics","₹15,000/month"),
("Data Analyst Intern","Clean datasets, prepare dashboards, and support business reporting.","Python, SQL, Excel","Students pursuing data or computer studies","₹18,000/month"),
("Cloud Engineering Intern","Support cloud deployments, monitoring, and infrastructure automation.","Linux, AWS, Git","Students with basic cloud knowledge","₹20,000/month"),
("Frontend Developer Intern","Build responsive interfaces and reusable UI components.","HTML, CSS, JavaScript","Freshers with frontend projects","₹16,000/month"),
("Data Engineering Intern","Help build ETL pipelines and validate data quality.","Python, SQL, ETL","Students with programming fundamentals","₹18,000/month"),
("Product Management Intern","Research user needs and support product planning.","Research, Excel, Communication","Final-year students and fresh graduates","₹15,000/month"),
("FinTech Software Intern","Develop features for financial workflows and internal tools.","Python, SQL, Git","Students with software fundamentals","₹20,000/month"),
("Sustainability Tech Intern","Analyze operational data for sustainability initiatives.","Excel, Data Analysis, Communication","Students interested in sustainability and analytics","₹14,000/month"),
("Java Developer Intern","Work with the engineering team on enterprise applications.","Java, Spring, SQL","Freshers with Java fundamentals","₹17,000/month"),
("E-commerce Operations Intern","Support catalog, order, and marketplace operations.","Excel, Analytics, Communication","Graduates with analytical skills","₹13,000/month"),
("QA Automation Intern","Create test cases and automate regression checks.","Python, Selenium, Git","Students with programming fundamentals","₹16,000/month"),
("DevOps Intern","Assist with CI/CD pipelines and deployment automation.","Git, Linux, Docker","Students with basic DevOps knowledge","₹20,000/month"),
("HealthTech Product Intern","Support product research and healthcare workflows.","Research, Documentation, Excel","Students interested in product technology","₹15,000/month"),
("Business Analyst Intern","Gather requirements and prepare process documentation.","Excel, SQL, Communication","Freshers with analytical skills","₹15,000/month"),
("Mobile App Developer Intern","Build and test features for mobile applications.","Flutter, Dart, Git","Students with mobile projects","₹18,000/month"),
("Mobility Data Intern","Analyze fleet and mobility datasets for insights.","Python, SQL, Visualization","Students with data analysis fundamentals","₹17,000/month"),
("UI/UX Design Intern","Create user flows, wireframes, and interface designs.","Figma, UX Research, Prototyping","Students with a design portfolio","₹15,000/month"),
("Machine Learning Intern","Prepare datasets and experiment with ML models.","Python, Pandas, scikit-learn","Students with ML coursework or projects","₹22,000/month"),
("Backend Developer Intern","Implement APIs and database-backed application features.","Python, APIs, SQL","Freshers with backend projects","₹18,000/month"),
("Digital Marketing Intern","Support campaigns and performance reporting.","Analytics, SEO, Communication","Graduates interested in digital marketing","₹12,000/month"),
("FoodTech Operations Intern","Analyze supply and fulfillment workflows.","Excel, Operations, Analytics","Students interested in operations","₹14,000/month"),
("Smart City Data Intern","Work with urban datasets and analytical reports.","Python, SQL, GIS","Students in technology or data","₹18,000/month"),
("Cybersecurity Intern","Assist with security reviews and vulnerability documentation.","Networking, Linux, Security Basics","Students with security fundamentals","₹20,000/month"),
("Robotics Software Intern","Support software modules for automation systems.","Python, C++, Git","Students with programming projects","₹22,000/month"),
("Cloud Applications Intern","Build and test cloud-native application components.","Python, Docker, Cloud Basics","Students with web or cloud projects","₹19,000/month")
]

JOBS = [
("Junior Software Engineer","Ship production features across backend and web services.","Python, Git, SQL","0–1 years / freshers","₹5.5 LPA"),("Associate Data Analyst","Create reports, dashboards, and business insights.","SQL, Excel, Power BI","0–2 years","₹5 LPA"),("Cloud Support Engineer","Support cloud workloads and troubleshoot infrastructure.","AWS, Linux, Networking","0–2 years","₹6 LPA"),("Frontend Developer","Develop accessible, responsive web applications.","JavaScript, React, CSS","0–2 years","₹6 LPA"),("Data Engineer","Build reliable pipelines and data processing workflows.","Python, SQL, ETL","1–2 years","₹7.5 LPA"),
("Associate Product Manager","Coordinate product discovery and delivery.","Product Thinking, Analytics, Communication","0–2 years","₹7 LPA"),("Software Engineer – Payments","Develop secure transaction services.","Java, APIs, SQL","0–2 years","₹7 LPA"),("Sustainability Analyst","Turn operational data into recommendations.","Excel, Analytics, Reporting","0–2 years","₹5 LPA"),("Java Software Engineer","Develop and maintain enterprise Java services.","Java, Spring Boot, SQL","0–2 years","₹6.5 LPA"),("E-commerce Analyst","Analyze sales and marketplace performance.","SQL, Excel, Analytics","0–2 years","₹5.5 LPA"),
("QA Engineer","Design automated tests and improve release quality.","Selenium, Python, API Testing","0–2 years","₹5.5 LPA"),("DevOps Engineer","Own CI/CD pipelines and deployment automation.","Docker, GitHub Actions, Linux","1–2 years","₹7 LPA"),("Product Operations Associate","Improve product workflows and operations.","Excel, SQL, Communication","0–2 years","₹5.5 LPA"),("Business Analyst","Translate requirements into technical deliverables.","SQL, Excel, Documentation","0–2 years","₹6 LPA"),("Flutter Developer","Build and maintain cross-platform mobile apps.","Flutter, Dart, REST APIs","0–2 years","₹6 LPA"),
("Mobility Operations Analyst","Optimize fleet operations using data.","SQL, Excel, Analytics","0–2 years","₹5.5 LPA"),("UI/UX Designer","Design product experiences from research to handoff.","Figma, UX, Prototyping","0–2 years","₹5 LPA"),("Machine Learning Engineer","Develop and evaluate machine learning solutions.","Python, ML, Pandas","0–2 years","₹8 LPA"),("Backend Engineer","Design APIs and services for scalable applications.","Python, Flask, PostgreSQL","0–2 years","₹7 LPA"),("Digital Marketing Executive","Run performance campaigns and analyze metrics.","SEO, Analytics, Ads","0–2 years","₹4.5 LPA"),
("Operations Analyst","Improve fulfillment workflows through data.","Excel, SQL, Operations","0–2 years","₹5 LPA"),("Data Platform Engineer","Build services for analytical workloads.","Python, SQL, Cloud","1–2 years","₹7.5 LPA"),("Security Analyst","Monitor security events and support vulnerability management.","Networking, Linux, Security Tools","0–2 years","₹6 LPA"),("Robotics Software Engineer","Develop software for robotic automation.","C++, Python, Robotics","0–2 years","₹7.5 LPA"),("Cloud Software Engineer","Develop and operate cloud-native services.","Python, Docker, Kubernetes","0–2 years","₹7.5 LPA")
]

def seed_demo_data(db, password):
    password_hash = generate_password_hash(password)
    for i, (company, org_type, location) in enumerate(COMPANIES):
        email = f"demo.employer{i+1}@fresherflow.local"
        row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if row:
            user_id = row[0]
        else:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)", (f"{company} Recruiting", email, password_hash, "employer"))
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        if not db.execute("SELECT id FROM employer_profiles WHERE user_id=?", (user_id,)).fetchone():
            db.execute("INSERT INTO employer_profiles(user_id,organization_name,organization_type,location,description,account_status,verification_status) VALUES(?,?,?,?,?,?,?)", (user_id, company, org_type, location, f"Demo employer profile for {company}.", "active", "verified"))
        source = INTERNSHIPS[i] if i < 25 else JOBS[i-25]
        title, description, skills, eligibility, salary = source
        if not db.execute("SELECT id FROM vacancies WHERE employer_id=? AND title=?", (user_id, title)).fetchone():
            db.execute("INSERT INTO vacancies(employer_id,title,vacancy_type,description,location,salary,skills,eligibility,deadline,status,moderation_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (user_id,title,"Internship" if i < 25 else "Entry-level Job",description,location,salary,skills,eligibility,"2026-12-31","active","approved"))
