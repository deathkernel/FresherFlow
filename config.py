import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

class Config:
    # Never ship a predictable fallback secret. Set SECRET_KEY in production;
    # a random per-process key keeps local development usable without a secret in source.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE = str(INSTANCE_DIR / "fresherflow.db")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads" / "resumes")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
