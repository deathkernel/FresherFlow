# FRESHERFLOW – ONLINE JOB PORTAL FOR FRESHERS

## Project Report

**P.D.E.A.'s Baburaoji Gholap College, Sangvi, Pune-411027**  
**Department of Software Development**  
**Submitted to Savitribai Phule Pune University**  
**Degree:** Bachelor of Vocational (Software Development) (Sem-III)  
**Academic Year:** 2026-2027  
**Project Guide:** Manisha Y. Khairnar  
**Head of Department:** Ms. S. A. Kadam

**Developed by:**  
1. ______________________________  
2. ______________________________

---

## Certificate

This project report is for **“FRESHERFLOW – ONLINE JOB PORTAL FOR FRESHERS”**, submitted as a requirement of the B.Voc Software Development course of Savitribai Phule Pune University for the academic year 2026-2027.

---

## Acknowledgement

We express our sincere gratitude to our project guide, Head of Department, lecturers, parents, family members and friends for their guidance, encouragement and support throughout the development of FresherFlow.

---

# Index

1. Introduction
2. System Analysis
3. Implementation Details – Software / Hardware Specifications
4. System Design
5. Testing
6. Conclusion and Recommendations
7. Future Scope
8. Bibliography and References

---

# 1. INTRODUCTION

FresherFlow is a Flask-based fresher recruitment platform designed to connect students looking for internships and entry-level jobs with employers posting opportunities. It provides separate Student, Employer and Admin workflows with SQLite persistence, resume uploads, vacancy management, applications and moderation.

The project is intended as a practical college-level web application. It focuses on simple UI, role separation, server-side validation and a normalized relational database.

## 1.1 Motivation

Freshers often have difficulty finding suitable opportunities because job information can be scattered across different platforms. FresherFlow provides a focused workflow for internships and entry-level jobs.

## 1.2 Problem Statement

The project addresses the need for a simple role-based recruitment workflow where students can find opportunities, employers can manage vacancies and applications, and administrators can moderate vacancies and control employer accounts.

## 1.3 Purpose / Objectives and Goals

- Develop a web-based recruitment portal for freshers.
- Provide separate Student, Employer and Admin panels.
- Allow students to maintain profiles, upload resumes, search vacancies, save opportunities and apply.
- Allow administrators to create employer accounts; allow employers to maintain organization profiles, create/edit vacancies, import vacancies from Excel and manage applications.
- Allow administrators to moderate vacancies and control employer accounts.
- Store application and vacancy information using SQLite.
- Apply server-side validation, CSRF protection and safe session configuration.

## 1.4 Literature Survey

The project follows common web application patterns including role-based access, relational persistence, form validation, CRUD operations, file uploads and workflow-based approval. The repository stack is Python 3.11+, Flask 3.x, SQLite, HTML/CSS/JavaScript and openpyxl for Excel vacancy import.

## 1.5 Project Scope and Limitations

**Scope:** Student registration/profile/resume, vacancy search, saving and applying; employer profiles, vacancy management, Excel import and application status management; admin moderation and employer management.

**Limitations:** The project is intended as a local/college web application. It does not implement a full commercial recruitment ecosystem, external job-board synchronization, payments, enterprise identity management or advanced recommendation algorithms.

---

# 2. SYSTEM ANALYSIS

## 2.1 Existing Systems

Existing recruitment systems generally provide job search, employer posting and application workflows. FresherFlow narrows the workflow to fresher-oriented internships and entry-level jobs and adds administrator-controlled moderation.

## 2.2 Scope and Limitations of Existing Systems

- Large recruitment platforms contain features unnecessary for a small academic project.
- Students may need to filter unrelated vacancies.
- Employer/admin workflows can be difficult to demonstrate in a simple classroom project.
- Commercial platforms may depend on external services and large-scale infrastructure.

## 2.3 Project Perspective and Features

| Module | Major Features |
|---|---|
| Student | Registration, profile, resume, vacancy search, save, apply, application tracking |
| Employer | Organization profile, vacancy management, Excel import, application status |
| Admin | Dashboard, application review, vacancy moderation, employer creation, suspension/activation/removal |

## 2.4 Stakeholders

| Stakeholder | Responsibility |
|---|---|
| Student | Find suitable fresher opportunities and submit applications |
| Employer | Publish vacancies and manage applications |
| Administrator | Moderate vacancies and control employer accounts |
| Project Guide / Department | Evaluate academic implementation and documentation |

## 2.5 Requirement Analysis

### Functional Requirements

- Student public registration and Student/Employer login.
- Student and employer profile management.
- Resume upload.
- Vacancy creation/editing.
- Internship and Entry-level Job vacancy types.
- Deadline validation.
- Student save/apply workflow.
- Employer application-status management.
- .xlsx bulk vacancy import.
- Admin vacancy moderation and employer management.

### Performance Requirements

- Reasonable response time for the local SQLite dataset.
- Parameterized database operations.
- Transactional bulk vacancy import.
- Resume upload limit of 5 MB.

### Security Requirements

- CSRF protection on POST requests.
- Password hashing.
- Role-based route protection.
- Employer ownership checks.
- Resume extension, size and signature validation.
- HTTP/HTTPS website URL validation.
- Configured production SECRET_KEY.
- Explicit production admin credentials.

---

# 3. IMPLEMENTATION DETAILS – SOFTWARE / HARDWARE SPECIFICATIONS

## 3.1 Software Specifications

| Component | Specification |
|---|---|
| Operating System | Windows / Linux / macOS |
| Language | Python 3.11+ |
| Framework | Flask 3.x |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Excel Processing | openpyxl |
| Development Server | Flask development server |
| Testing | pytest-based project tests |

## 3.2 Hardware Specifications

| Component | Recommended Academic Setup |
|---|---|
| Processor | Dual-core or better |
| RAM | 4 GB or more |
| Storage | At least 1 GB free |
| Display | 1366 × 768 or higher |
| Network | Not required for normal local operation after dependencies are installed |

## 3.3 Technology Architecture

The Flask application receives requests through route modules, validates input, uses SQLite for persistence and renders HTML templates. JavaScript provides client-side interactions while the security module provides CSRF, upload and URL validation helpers.

## 3.4 Main Project Structure

| Component | Purpose |
|---|---|
| app.py | Flask application, blueprints, security headers and global form protection |
| config.py | Configuration, database, uploads, sessions and admin configuration |
| security.py | CSRF, resume upload and website URL validation |
| database/database.py | SQLite connection, schema initialization and migrations |
| database/schema.sql | Relational database schema |
| routes/auth_routes.py | Registration/login/logout |
| routes/student_routes.py | Student workflow |
| routes/employer_routes.py | Employer workflow |
| routes/admin_routes.py | Admin workflow |
| static/js/ | Client-side interactions |
| templates/ | Role-specific and shared HTML pages |

---

# 4. SYSTEM DESIGN

## 4.1 Normalized Database Design and Data Dictionary

The database separates users from role-specific profiles and separates vacancies, applications and saved jobs into related tables. Primary keys identify records, foreign keys maintain relationships and unique constraints prevent duplicate applications and duplicate saved-job records.

### Database Tables

| Table | Purpose | Important Fields |
|---|---|---|
| users | Login identity and role | id, name, email, password_hash, role |
| student_profiles | Student information | user_id, phone, education, college, skills, resume_filename |
| employer_profiles | Organization and account state | user_id, organization_name, website, account_status |
| vacancies | Job/internship opportunities | employer_id, title, vacancy_type, deadline, status, moderation_status |
| applications | Student applications | vacancy_id, student_id, status, applied_at |
| saved_jobs | Saved opportunities | vacancy_id, student_id, created_at |

### Key Field Rules

| Field | Rule |
|---|---|
| users.role | student or employer |
| vacancies.vacancy_type | Internship or Entry-level Job |
| vacancies.status | draft, active or closed |
| vacancies.moderation_status | pending, approved or rejected |
| employer_profiles.account_status | active or suspended |
| applications.status | Applied, Shortlisted, Selected or Rejected |

## 4.2 Data Model – Functional Decomposition Diagram

The functional decomposition of FresherFlow is:

FRESHERFLOW
- Authentication
  - Student Registration / Login
  - Employer Account Provisioning / Login
- Student Module
  - Dashboard
  - Profile / Resume
  - Search Vacancies
  - Save Vacancy
  - Apply
  - Track Applications
- Employer Module
  - Dashboard
  - Organization Profile
  - Create / Edit Vacancy
  - Bulk Excel Import
  - Application Status Management
- Admin Module
  - Dashboard
  - Vacancy Moderation
  - Employer Management
  - Student / Application Review

## 4.3 User Interfaces

### 4.3.1 Menus

| Panel | Primary Menu |
|---|---|
| Student | Dashboard, Jobs, Applications, Profile |
| Employer | Dashboard, My Vacancies, Post Vacancy, Bulk Vacancies, Applications, Organization Profile |
| Admin | Overview, Applications, Companies, Moderation and account controls |

### 4.3.2 Input Screens

Student Profile, Employer Profile, Post Vacancy, Bulk Vacancy Import, Student Apply/Save and Admin Add Employer are the principal input screens.

### 4.3.3 Output Screens

The system provides student vacancy cards/job details/application lists, employer vacancy/application lists and admin application/company-management views.

### 4.4 Reports / Graphs

- Student: applications, shortlisted, selected, saved and available jobs.
- Employer: active vacancies, applications, shortlisted and selected applications.
- Admin: companies, active companies, pending/approved/rejected jobs and total applications.

---

# 5. TESTING

Testing covers route authorization, input validation, database constraints, vacancy workflow rules and security controls. The cases below describe the implemented validation behavior; the final local test command should be run before submission.

## 5.1 Black Box / Data Validation Test Cases

| ID | Test | Expected Result |
|---|---|---|
| TC-01 | Valid student registration | Student account/profile created |
| TC-02 | Short password | Registration rejected |
| TC-03 | Invalid resume extension | Upload rejected |
| TC-04 | Resume over 5 MB | Upload rejected |
| TC-05 | Past vacancy deadline | Validation fails |
| TC-06 | Entry-level role requiring prior experience | Validation fails |
| TC-07 | Direct application to unavailable job | Application rejected |
| TC-08 | Direct save of unavailable job | Save rejected |
| TC-09 | Employer modifies another employer's vacancy | Access denied |
| TC-10 | Admin approves expired vacancy | Approval rejected |
| TC-11 | Bulk .xlsx import | Rows validated before insertion |
| TC-12 | Invalid website URL | Value rejected |

## 5.2 Functional Validation

| ID | Workflow | Validation |
|---|---|---|
| FV-01 | Student Registration/Login → Dashboard | Student dashboard |
| FV-02 | Admin creates employer → Employer Login → Dashboard | Active employer dashboard |
| FV-03 | Suspended Employer Login | Employer workflow blocked |
| FV-04 | Student Search → Details | Only available approved vacancies shown |
| FV-05 | Student Apply | Single application / duplicate prevented |
| FV-06 | Employer Application Status | Ownership enforced |
| FV-07 | Admin Moderation | Approve/reject workflow |
| FV-08 | Admin Employer Management | Add/suspend/activate/remove |

## 5.3 Security Validation

- POST requests are protected with CSRF tokens.
- Role decorators prevent cross-panel access.
- User-supplied SQL values use parameter placeholders.
- Resume uploads use extension, size and file-signature checks.
- Website links are restricted to absolute HTTP/HTTPS URLs.
- Production session cookies support Secure, HttpOnly and SameSite=Lax configuration.

## 5.4 Final Testing Note

Before printing the report, run:

    python -m pytest -q

Then manually walk through Student, Employer and Admin flows in the local application.

---

# 6. CONCLUSION AND RECOMMENDATIONS

FresherFlow demonstrates an academic recruitment workflow with separate Student, Employer and Admin responsibilities. It combines Flask, SQLite, HTML/CSS/JavaScript, resume handling and Excel import into one manageable application.

The implementation emphasizes server-side validation and role separation. Vacancy deadlines, moderation state, employer account state and application ownership are checked by the backend.

### Recommendations

- Run the complete test suite before final demonstration.
- Perform a manual Student/Employer/Admin walkthrough.
- Use a strong configured SECRET_KEY and explicit admin credentials outside local development.
- Keep runtime databases, generated secrets and uploaded resumes outside source control.
- Add final screenshots from the working application to the printed report.

---

# 7. FUTURE SCOPE

1. Email notifications for application and moderation events.
2. Password reset and account recovery.
3. Pagination and advanced filtering.
4. Employer verification with supporting documents.
5. Skill-based vacancy recommendations.
6. Analytics dashboards and exportable reports.
7. Cloud deployment with managed database/object storage.
8. Administrator audit logs.
9. Integration with external job boards or institutional placement systems.

---

# 8. BIBLIOGRAPHY AND REFERENCES

1. FresherFlow Project Repository – deathkernel/FresherFlow.
2. Python Documentation – Python language and standard-library reference.
3. Flask Documentation – Flask web application framework reference.
4. SQLite Documentation – SQLite relational database documentation.
5. openpyxl Documentation – Excel workbook processing library.
6. Savitribai Phule Pune University / P.D.E.A.'s Baburaoji Gholap College project-report format supplied for this project.

---

## Appendix A – Final Demonstration Checklist

| Area | Demonstration | Expected |
|---|---|---|
| Student | Register → Login → Profile | Student account/profile works |
| Student | Search → Details → Save | Available vacancy can be saved |
| Student | Apply | Application is created once |
| Employer | Login → Post Vacancy | Vacancy enters moderation workflow |
| Admin | Review vacancy | Admin can approve/reject |
| Employer | View applications | Employer applications appear |
| Employer | Update application status | Status changes are reflected |
| Admin | Add/Suspend/Remove employer | Employer management works |

## Appendix B – Submission Notes

Student names and signatures are left blank because the supplied college format contains blank candidate fields. Replace them with the actual names, insert final application screenshots and update the test-results section with the final local test run.
