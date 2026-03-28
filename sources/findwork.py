"""Findwork.dev — API focused on software development jobs."""

import logging
from models import Job
from sources.http_utils import get_json
from config import FINDWORK_API_KEY
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

URL = "https://findwork.dev/api/jobs/"


def fetch_findwork() -> list[Job]:
    """Fetch remote software jobs from Findwork.dev."""
    if not FINDWORK_API_KEY:
        log.warning("Findwork: API key not set — skipping.")
        return []

    headers = {"Authorization": f"Token {FINDWORK_API_KEY}"}
    jobs = []
    searches = [
        "software engineer", "backend developer", "frontend developer",
        "flutter developer", "mobile developer", "data scientist",
        "devops engineer", "machine learning", "cybersecurity",
        "blockchain developer", "game developer", "QA engineer",
        "odoo developer", "SAP developer", "salesforce developer",
        "digital marketing", "growth marketing",
        "data engineer", "analytics engineer",
        "application support",
    ]

    max_workers = min(10, max(2, len(searches)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_search = {ex.submit(get_json, URL, params={"search": s, "remote": "true"}, headers=headers): s for s in searches}
        for fut in as_completed(future_to_search):
            try:
                data = fut.result()
            except Exception as e:
                log.warning(f"Findwork query failed: {e}")
                continue
            if not data or "results" not in data:
                continue
            for item in data["results"]:
                keywords = item.get("keywords", []) or []

                jobs.append(Job(
                    title=item.get("role", ""),
                    company=item.get("company_name", ""),
                    location=item.get("location", "Remote"),
                    url=item.get("url", ""),
                    source="findwork",
                    salary="",
                    job_type=item.get("employment_type", ""),
                    tags=keywords,
                    is_remote=item.get("remote", False),
                ))
    log.info(f"Findwork: fetched {len(jobs)} jobs.")
    return jobs
