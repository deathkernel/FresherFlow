"""Public job API clients and normalization for FresherFlow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

TIMEOUT = 20
USER_AGENT = "FresherFlow/1.0 (+https://github.com/deathkernel/FresherFlow)"


def _get(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value).strip()


def _iso(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return text


def fetch_himalayas() -> list[dict[str, Any]]:
    data = _get("https://himalayas.app/jobs/api", {"limit": 20})
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    result = []
    for job in jobs:
        result.append({
            "source": "himalayas",
            "source_id": _text(job.get("id") or job.get("slug") or job.get("title")),
            "title": _text(job.get("title")),
            "company": _text(job.get("companyName") or job.get("company", {}).get("name")),
            "location": _text(job.get("location") or job.get("locationRestrictions") or "Remote"),
            "job_type": _text(job.get("employmentType") or "Entry-level Job"),
            "description": _text(job.get("description") or job.get("excerpt")),
            "skills": _text(job.get("skills") or job.get("categories")),
            "salary": _text(job.get("salary")),
            "apply_url": _text(job.get("applicationLink") or job.get("url")),
            "posted_at": _iso(job.get("pubDate") or job.get("publishedAt")),
            "source_url": _text(job.get("url") or "https://himalayas.app"),
        })
    return result


def fetch_jobicy() -> list[dict[str, Any]]:
    data = _get("https://jobicy.com/api/v2/remote-jobs", {"count": 200})
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    result = []
    for job in jobs:
        result.append({
            "source": "jobicy",
            "source_id": _text(job.get("id") or job.get("jobSlug")),
            "title": _text(job.get("jobTitle")),
            "company": _text(job.get("companyName")),
            "location": _text(job.get("jobGeo") or "Remote"),
            "job_type": _text(job.get("jobType") or "Entry-level Job"),
            "description": _text(job.get("jobDescription") or job.get("jobExcerpt")),
            "skills": _text(job.get("jobIndustry")),
            "salary": _salary(job),
            "apply_url": _text(job.get("url")),
            "posted_at": _iso(job.get("pubDate")),
            "source_url": _text(job.get("url") or "https://jobicy.com"),
        })
    return result


def _salary(job: dict[str, Any]) -> str:
    minimum, maximum, currency = job.get("salaryMin"), job.get("salaryMax"), job.get("salaryCurrency")
    if minimum is None and maximum is None:
        return ""
    if minimum is not None and maximum is not None:
        return f"{currency or ''} {minimum:g}–{maximum:g}".strip()
    return f"{currency or ''} {minimum if minimum is not None else maximum:g}".strip()


def fetch_all() -> tuple[list[dict[str, Any]], dict[str, str]]:
    jobs: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for name, fetcher in (("himalayas", fetch_himalayas), ("jobicy", fetch_jobicy)):
        try:
            jobs.extend(fetcher())
        except requests.RequestException as exc:
            errors[name] = f"HTTP error: {exc}"
        except (KeyError, TypeError, ValueError) as exc:
            errors[name] = f"Invalid response: {exc}"
    return jobs, errors
