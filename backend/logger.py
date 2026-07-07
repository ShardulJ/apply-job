import csv
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "output", "applications_log.csv")

FIELDNAMES = [
    "timestamp",
    "company",
    "job_title",
    "resume_used",
    "match_score",
    "tier",
    "decision",
    "style_violations",
]


def log_application(
    company: str,
    job_title: str,
    resume_used: str | None,
    match_score: float,
    tier: str,
    decision: str,
    style_violations: list[str],
    log_path: str = LOG_PATH,
) -> None:
    file_exists = os.path.exists(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "company": company,
            "job_title": job_title,
            "resume_used": resume_used,
            "match_score": match_score,
            "tier": tier,
            "decision": decision,
            "style_violations": ", ".join(style_violations),
        })


if __name__ == "__main__":
    log_application(
        company="Acme Corp",
        job_title="Backend Engineer",
        resume_used="backend_resume.txt",
        match_score=82.5,
        tier="full",
        decision="apply",
        style_violations=[],
    )

    log_application(
        company="Globex Inc",
        job_title="Backend Engineer",
        resume_used="backend_resume.txt",
        match_score=78.0,
        tier="full",
        decision="flag",
        style_violations=["leverage", "synergy"],
    )

    print(f"Logged rows to {LOG_PATH}")
    with open(LOG_PATH) as f:
        print(f.read())
