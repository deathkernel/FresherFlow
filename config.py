import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
SECRET_FILE = INSTANCE_DIR / ".secret_key"


def local_secret():
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    value = secrets.token_hex(32)
    SECRET_FILE.write_text(value, encoding="utf-8")
    return value


class Config:
    # Flask sessions need a signing key. It is generated locally and never stored in source.
    SECRET_KEY = os.environ.get("SECRET_KEY") or local_secret()
    DATABASE = str(INSTANCE_DIR / "fresherflow.db")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads" / "resumes")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
