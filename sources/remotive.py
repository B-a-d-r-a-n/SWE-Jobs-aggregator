"""Remotive — remote jobs API (software-dev, qa, devops-sysadmin, marketing, data)."""

import logging
from models import Job
from sources.http_utils import get_json
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

BASE = "https://remotive.com/api/remote-jobs"
CATEGORIES = ["software-dev", "qa", "devops-sysadmin", "marketing", "data"]


def fetch_remotive() -> list[Job]:
    """Fetch jobs from Remotive across multiple categories."""
    jobs: list[Job] = []
    max_workers = min(8, max(2, len(CATEGORIES)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_cat = {ex.submit(get_json, BASE, params={"category": cat, "limit": 50}): cat for cat in CATEGORIES}
        for fut in as_completed(future_to_cat):
            cat = future_to_cat[fut]
            try:
                data = fut.result()
            except Exception as e:
                log.warning(f"Remotive category {cat} failed: {e}")
                continue
            if not data or "jobs" not in data:
                log.warning(f"Remotive: no data for category={cat}")
                continue
            for item in data["jobs"]:
                jobs.append(Job(
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("candidate_required_location", "Anywhere"),
                    url=item.get("url", ""),
                    source="remotive",
                    salary=item.get("salary", ""),
                    job_type=item.get("job_type", "").replace("_", " ").title(),
                    tags=[item.get("category", "")],
                    is_remote=True,
                ))
    log.info(f"Remotive: fetched {len(jobs)} jobs.")
    return jobs
