from io import BytesIO

from werkzeug.datastructures import FileStorage

from security import valid_resume_upload


def upload(name, data):
    return FileStorage(stream=BytesIO(data), filename=name)


def test_accepts_pdf_signature():
    assert valid_resume_upload(upload("resume.pdf", b"%PDF-1.7\nexample"))


def test_rejects_fake_pdf():
    assert not valid_resume_upload(upload("resume.pdf", b"not a pdf"))


def test_accepts_doc_signature():
    assert valid_resume_upload(
        upload("resume.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x")
    )


def test_accepts_docx_zip_signature():
    assert valid_resume_upload(upload("resume.docx", b"PK\x03\x04" + b"x"))


def test_rejects_disallowed_extension():
    assert not valid_resume_upload(upload("resume.exe", b"MZ"))


def test_rejects_oversized_upload():
    assert not valid_resume_upload(
        upload("resume.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024))
    )


def test_website_url_validation():
    from security import valid_website_url

    assert valid_website_url("https://example.com")
    assert valid_website_url("http://example.com/path")
    assert valid_website_url("")
    assert not valid_website_url("javascript:alert(1)")
    assert not valid_website_url("//evil.example")
