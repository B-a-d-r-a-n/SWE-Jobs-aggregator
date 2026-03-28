"""Reed.co.uk — UK job board aggregator API (free, needs API key)."""

import logging
import base64
from models import Job
from sources.http_utils import get_json
from config import REED_API_KEY
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

URL = "https://www.reed.co.uk/api/1.0/search"

SEARCHES = [
    {"keywords": "software developer remote", "resultsToTake": 25},
    {"keywords": "backend developer remote", "resultsToTake": 25},
    {"keywords": "flutter developer remote", "resultsToTake": 15},
    {"keywords": "devops engineer remote", "resultsToTake": 15},
    {"keywords": "data scientist remote", "resultsToTake": 15},
]


def fetch_reed() -> list[Job]:
    """Fetch remote software jobs from Reed.co.uk."""
    if not REED_API_KEY:
        log.warning("Reed: API key not set — skipping.")
        return []

    # Reed uses Basic auth with API key as username, empty password
    auth_str = base64.b64encode(f"{REED_API_KEY}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth_str}"}

    jobs: list[Job] = []
    max_workers = min(8, max(2, len(SEARCHES)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_params = {ex.submit(get_json, URL, params=params, headers=headers): params for params in SEARCHES}
        for fut in as_completed(future_to_params):
            try:
                data = fut.result()
            except Exception as e:
                log.warning(f"Reed query failed: {e}")
                continue
            if not data or not isinstance(data, dict):
                continue
            results = data.get("results", [])
            for item in results:
                salary = ""
                if item.get("minimumSalary") and item.get("maximumSalary"):
                    try:
                        salary = f"£{item['minimumSalary']:,.0f}–£{item['maximumSalary']:,.0f}"
                    except Exception:
                        salary = ""

                job_url = item.get("jobUrl", "")

                jobs.append(Job(
                    title=item.get("jobTitle", ""),
                    company=item.get("employerName", ""),
                    location=item.get("locationName", ""),
                    url=job_url,
                    source="reed",
                    salary=salary,
                    job_type=item.get("contractType", ""),
                    tags=[],
                    is_remote="remote" in item.get("jobTitle", "").lower() or
                              "remote" in item.get("jobDescription", "").lower()[:200],
                ))
    log.info(f"Reed: fetched {len(jobs)} jobs.")
    return jobs
