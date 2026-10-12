from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

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


def test_accepts_real_docx_container():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    assert valid_resume_upload(upload("resume.docx", stream.getvalue()))

def test_rejects_fake_docx_zip_signature():
    assert not valid_resume_upload(upload("resume.docx", b"PK\x03\x04" + b"x"))


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



def test_rejects_docx_with_traversal_entry():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("../outside.txt", "not allowed")
    assert not valid_resume_upload(upload("resume.docx", stream.getvalue()))


def test_rejects_docx_with_oversized_uncompressed_member():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "x" * (5 * 1024 * 1024 + 1))
    assert not valid_resume_upload(upload("resume.docx", stream.getvalue()))


def test_rejects_empty_resume():
    assert not valid_resume_upload(upload("resume.pdf", b""))



def test_rejects_docx_with_windows_style_traversal_entry():
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr(r"word\\..\\..\\outside.txt", "not allowed")
    assert not valid_resume_upload(upload("resume.docx", stream.getvalue()))


def test_rejects_docx_with_excessive_total_uncompressed_size():
    stream = BytesIO()
    payload = b"x" * (4 * 1024 * 1024)
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        for index in range(7):
            archive.writestr(f"word/media/image{index}.bin", payload)
    assert len(stream.getvalue()) < 5 * 1024 * 1024
    assert not valid_resume_upload(upload("resume.docx", stream.getvalue()))
