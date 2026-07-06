import os

MOCK_LABEL = "[MOCK RESPONSE - ANTHROPIC_API_KEY not set]"

STYLE_RULES = """
Style rules for the rewrite:
- Do not use AI-sounding words like "leverage" or "utilize"
- Do not use em dashes
- Do not use weak verbs like "helped" or "assisted"
- Keep the resume's chronological order exactly as it is
- List skills comma separated
- Write in a human tone that passes AI detectors
"""


def rewrite_weak_bullets(
    job_description: str, resume: dict[str, str], model: str = "claude-sonnet-5"
) -> dict[str, str | bool]:
    filename = resume["filename"]
    resume_text = resume["text"]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "filename": filename,
            "rewritten_bullets": f"{MOCK_LABEL}\nSet ANTHROPIC_API_KEY to generate a real rewrite.",
            "mock": True,
        }

    try:
        import anthropic
    except ImportError:
        return {
            "filename": filename,
            "rewritten_bullets": f"{MOCK_LABEL}\nThe anthropic package is not installed.",
            "mock": True,
        }

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Job description:
{job_description}

Resume ({filename}):
{resume_text}

Identify the 2-3 weakest bullet points in this resume relative to the job description
above, and rewrite only those bullet points so they better match the job.

{STYLE_RULES}

Return only the rewritten bullet points, one per line. Do not return the full resume
and do not add any commentary."""

    response = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    rewritten_bullets = response.content[0].text.strip()

    return {
        "filename": filename,
        "rewritten_bullets": rewritten_bullets,
        "mock": False,
    }


if __name__ == "__main__":
    sample_jd = """
    We are looking for a Backend Engineer with strong experience in Python,
    FastAPI, REST APIs, and relational databases such as PostgreSQL. Experience
    with Docker, CI/CD pipelines, and cloud platforms like AWS is a plus.
    """

    sample_resume = {
        "filename": "backend_resume.txt",
        "text": """
        Backend Developer, Acme Corp, 2021-2024
        - Helped the team build REST APIs using Python and FastAPI
        - Assisted with deploying services on AWS
        - Wrote unit tests for internal tools

        Skills: Python, FastAPI, PostgreSQL, Docker, AWS
        """,
    }

    result = rewrite_weak_bullets(sample_jd, sample_resume)
    print(f"Filename: {result['filename']}")
    print(f"Mock: {result['mock']}")
    print(result["rewritten_bullets"])
