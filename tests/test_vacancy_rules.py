from datetime import date, timedelta
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from routes.employer_routes import deadline_invalid, vacancy_form
from routes.student_routes import deadline_passed


def test_deadline_validation_accepts_today_and_future():
    assert not deadline_invalid(date.today().isoformat())
    assert not deadline_invalid((date.today() + timedelta(days=1)).isoformat())


def test_deadline_validation_rejects_past_and_invalid_dates():
    assert deadline_invalid((date.today() - timedelta(days=1)).isoformat())
    assert deadline_invalid("not-a-date")


def test_vacancy_form_rejects_past_deadline():
    data, error = vacancy_form(
        {
            "title": "Python Developer",
            "vacancy_type": "Entry-level Job",
            "location": "Pune",
            "description": "Build web applications.",
            "eligibility": "Freshers",
            "deadline": (date.today() - timedelta(days=1)).isoformat(),
        }
    )
    assert data is None
    assert "deadline" in error.lower()


def test_student_deadline_check_handles_missing_and_past_dates():
    assert not deadline_passed(None)
    assert not deadline_passed(date.today().isoformat())
    assert deadline_passed((date.today() - timedelta(days=1)).isoformat())
    assert deadline_passed("invalid")


def test_entry_level_rejects_numeric_experience_requirements():
    from routes.employer_routes import experience_requirement_invalid

    assert experience_requirement_invalid("Entry-level Job", "Minimum 2+ years of experience")
    assert experience_requirement_invalid("Entry-level Job", "3 yrs experience required")


def test_entry_level_allows_explicit_no_experience():
    from routes.employer_routes import experience_requirement_invalid

    assert not experience_requirement_invalid("Entry-level Job", "No prior experience required")
    assert not experience_requirement_invalid("Entry-level Job", "Freshers welcome, no experience needed")



def test_excel_import_rejects_zip_bomb_before_workbook_parsing():
    from routes.employer_routes import excel_vacancy_forms

    stream = BytesIO()
    payload = b"x" * (4 * 1024 * 1024)
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for index in range(7):
            archive.writestr(f"xl/sharedStrings{index}.xml", payload)
    compressed = stream.getvalue()
    assert len(compressed) < 5 * 1024 * 1024

    vacancies, error = excel_vacancy_forms(
        FileStorage(stream=BytesIO(compressed), filename="bulk.xlsx")
    )
    assert vacancies is None
    assert "safety limits" in error.lower()
