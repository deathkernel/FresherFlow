"""Stable vacancy identity and duplicate lookup helpers."""
import hashlib
import json
import re
import secrets

def normalize_vacancy_value(value):
    """Normalize case, whitespace and punctuation without fuzzy matching."""
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()

def vacancy_fingerprint(employer_id, data):
    """Fingerprint exact normalized vacancy content within one employer."""
    identity = {"employer_id": int(employer_id), "title": normalize_vacancy_value(data.get("title")), "vacancy_type": normalize_vacancy_value(data.get("vacancy_type")), "location": normalize_vacancy_value(data.get("location")), "description": normalize_vacancy_value(data.get("description"))}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()

def new_vacancy_code():
    """Return a human-readable, collision-resistant vacancy reference."""
    return f"FF-JOB-{secrets.token_hex(6).upper()}"

def find_duplicate_vacancy(db, employer_id, data, exclude_id=None):
    fingerprint = vacancy_fingerprint(employer_id, data)
    sql = "SELECT id, vacancy_code, title, status FROM vacancies WHERE employer_id=? AND dedupe_fingerprint=?"
    params = [employer_id, fingerprint]
    if exclude_id is not None:
        sql += " AND id<>?"
        params.append(exclude_id)
    sql += " ORDER BY id ASC LIMIT 1"
    return db.execute(sql, params).fetchone()
