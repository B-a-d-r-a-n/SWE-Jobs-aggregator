"""Himalayas — free remote jobs API (no key required)."""

import logging
from models import Job
from sources.http_utils import get_json
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

BASE = "https://himalayas.app/jobs/api/search"
QUERIES = [
    "software engineer", "backend developer", "frontend developer",
    "devops", "QA engineer", "full stack developer",
    "flutter developer", "mobile developer", "react native",
    "data scientist", "machine learning", "blockchain developer",
    "cybersecurity engineer", "game developer", "unity developer",
    "odoo developer", "SAP developer", "ERP developer",
    "salesforce developer", "intern software",
    "digital marketing", "social media marketing", "growth marketing",
    "data engineer", "analytics engineer",
    "application support", "technical support engineer",
]


def fetch_himalayas() -> list[Job]:
    """Fetch jobs from Himalayas across multiple queries."""
    jobs: list[Job] = []
    max_workers = min(10, max(2, len(QUERIES)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_q = {ex.submit(get_json, BASE, params={"query": q, "limit": 20}): q for q in QUERIES}
        for fut in as_completed(future_to_q):
            try:
                data = fut.result()
            except Exception as e:
                log.warning(f"Himalayas query failed: {e}")
                continue
            if not data or "jobs" not in data:
                continue
            for item in data["jobs"]:
                location = item.get("location", "")
                remote = item.get("timezoneRestriction") is not None or "remote" in location.lower()
                jobs.append(Job(
                    title=item.get("title", ""),
                    company=item.get("companyName", ""),
                    location=location or "Remote",
                    url=item.get("applicationLink") or f"https://himalayas.app/jobs/{item.get('slug', '')}",
                    source="himalayas",
                    salary=_format_salary(item),
                    job_type=item.get("employmentType", ""),
                    tags=item.get("categories", []) or [],
                    is_remote=remote,
                ))
    log.info(f"Himalayas: fetched {len(jobs)} jobs.")
    return jobs


def _format_salary(item: dict) -> str:
    mn = item.get("salaryCurrencyMin")
    mx = item.get("salaryCurrencyMax")
    cur = item.get("salaryCurrency", "USD")
    if mn and mx:
        return f"{cur} {mn:,}–{mx:,}"
    return ""
