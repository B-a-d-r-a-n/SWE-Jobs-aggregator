"""Jobicy — free remote jobs API."""

import logging
from models import Job
from sources.http_utils import get_json
from concurrent.futures import ThreadPoolExecutor, as_completed

log = logging.getLogger(__name__)

BASE = "https://jobicy.com/api/v2/remote-jobs"
INDUSTRIES = ["dev", "engineering", "marketing"]


def fetch_jobicy() -> list[Job]:
    """Fetch jobs from Jobicy across dev and engineering categories."""
    jobs: list[Job] = []
    max_workers = min(6, max(2, len(INDUSTRIES)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_to_ind = {ex.submit(get_json, BASE, params={"count": 50, "industry": ind}): ind for ind in INDUSTRIES}
        for fut in as_completed(future_to_ind):
            try:
                data = fut.result()
            except Exception as e:
                log.warning(f"Jobicy query failed: {e}")
                continue
            if not data or "jobs" not in data:
                continue
            for item in data["jobs"]:
                salary_parts = []
                if item.get("annualSalaryMin"):
                    salary_parts.append(str(item["annualSalaryMin"]))
                if item.get("annualSalaryMax"):
                    salary_parts.append(str(item["annualSalaryMax"]))
                salary = "–".join(salary_parts) if salary_parts else ""

                jobs.append(Job(
                    title=item.get("jobTitle", ""),
                    company=item.get("companyName", ""),
                    location=item.get("jobGeo", "Remote"),
                    url=item.get("url", ""),
                    source="jobicy",
                    salary=salary,
                    job_type=item.get("jobType", ""),
                    tags=[item.get("jobIndustry", "")] if item.get("jobIndustry") else [],
                    is_remote=True,
                ))
    log.info(f"Jobicy: fetched {len(jobs)} jobs.")
    return jobs
