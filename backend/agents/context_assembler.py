import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resume_picker import pick_best_resume
from screener import screen_resume


def assemble_context(job_description: str, resumes: list[dict]) -> dict:
    best_resume = pick_best_resume(job_description, resumes)
    tier = screen_resume(job_description, best_resume["text"])["tier"]

    assembled_context = f"""Job description:
{job_description.strip()}

Candidate resume ({best_resume['filename']}):
{best_resume['text'].strip()}

Metadata:
- match score: {best_resume['score']}
- tier: {tier}"""

    return {
        "job_description": job_description,
        "best_resume": best_resume,
        "tier": tier,
        "assembled_context": assembled_context,
    }


if __name__ == "__main__":
    sample_jd = """
    We are looking for a Backend Engineer with strong experience in Python,
    FastAPI, REST APIs, and relational databases such as PostgreSQL. Experience
    with Docker, CI/CD pipelines, and cloud platforms like AWS is a plus.
    """

    sample_resumes = [
        {
            "filename": "backend_resume.txt",
            "text": """
            Backend developer with 4 years of experience building REST APIs using
            Python and FastAPI. Skilled in PostgreSQL, Docker, and deploying services
            on AWS. Familiar with setting up CI/CD pipelines using GitHub Actions.
            """,
        },
        {
            "filename": "frontend_resume.txt",
            "text": """
            Frontend developer specializing in React, TypeScript, and building
            responsive UIs. Experienced with CSS frameworks and design systems.
            """,
        },
    ]

    result = assemble_context(sample_jd, sample_resumes)
    print(f"Best resume: {result['best_resume']['filename']}")
    print(f"Tier: {result['tier']}")
    print("\n--- Assembled context ---")
    print(result["assembled_context"])
