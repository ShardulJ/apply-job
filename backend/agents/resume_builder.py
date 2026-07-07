import json
import os

MOCK_LABEL = "[MOCK RESPONSE - ANTHROPIC_API_KEY not set]"

STYLE_RULES = """
Style rules for the new resume:
- One page only
- No AI-sounding words like "leverage", "utilize", "spearhead", or "impactful"
- No em dashes
- No dashes of any kind inside bullet points
- Write in a human tone that passes AI detectors
- Preserve the chronological order of experiences exactly as they appear
  across the source resumes
- List skills comma separated
- Education section goes above the experience section
- Profile summary goes at the very top
- Use Boston, MA as the location if no location is given anywhere in the
  source resumes
"""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def build_tailored_resume(
    job_description: str, resumes: list[dict[str, str]], model: str = "claude-sonnet-5"
) -> dict:
    sources = [resume["filename"] for resume in resumes]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "resume_text": f"{MOCK_LABEL}\nSet ANTHROPIC_API_KEY to generate a real tailored resume.",
            "bullets_used": [],
            "sources": sources,
            "mock": True,
        }

    try:
        import anthropic
    except ImportError:
        return {
            "resume_text": f"{MOCK_LABEL}\nThe anthropic package is not installed.",
            "bullets_used": [],
            "sources": sources,
            "mock": True,
        }

    client = anthropic.Anthropic(api_key=api_key)

    resumes_block = "\n\n".join(
        f"Resume ({resume['filename']}):\n{resume['text']}" for resume in resumes
    )

    prompt = f"""Job description:
{job_description}

Source resumes:
{resumes_block}

Read all of the source resumes above and extract the most relevant bullet
points, skills, and experiences across all of them for this specific job.
Construct one new tailored resume from that material.

{STYLE_RULES}

Respond with only a JSON object (no markdown formatting, no commentary)
with exactly these keys:
- "resume_text": the full tailored resume as plain text
- "bullets_used": a list of the original bullet points, verbatim from the
  source resumes, that were selected for the new resume
- "sources": a list of the source resume filenames that contributed content
"""

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = next(
        block.text for block in response.content if block.type == "text"
    )
    result = json.loads(_strip_code_fence(raw_text))

    return {
        "resume_text": result["resume_text"],
        "bullets_used": result["bullets_used"],
        "sources": result["sources"],
        "mock": False,
    }


if __name__ == "__main__":
    sample_jd = """
    Senior ML engineer needed to build RAG pipelines, semantic retrieval systems,
    and evaluation frameworks in production. Strong background in embedding-based
    retrieval, backend APIs, and AWS deployment.
    """

    sample_resumes = [
        {
            "filename": "resume_a.txt",
            "text": """
            Jane Doe
            Profile: Senior ML engineer with 5 years building production ML systems.
            Education: MS Computer Science, DePaul University, 2023-2025
            Experience:
            ML Engineer, Acme AI, 2023-2025
            - Built RAG pipelines for enterprise document search
            - Designed evaluation frameworks to measure retrieval quality
            - Deployed backend APIs on AWS serving low-latency inference

            Skills: Python, PyTorch, AWS, Docker, FastAPI
            """,
        },
        {
            "filename": "resume_b.txt",
            "text": """
            Jane Doe
            Profile: ML engineer with experience in NLP and data pipelines.
            Education: BS Computer Science, State University, 2019-2023
            Experience:
            Data Scientist, Beta Corp, 2021-2023
            - Built classification models for customer support tickets
            - Automated data pipelines using Airflow

            Skills: Python, SQL, Airflow, scikit-learn
            """,
        },
    ]

    result = build_tailored_resume(sample_jd, sample_resumes)
    print(f"Mock: {result['mock']}")
    print(f"Sources: {result['sources']}")
    print(f"\nBullets used:\n{result['bullets_used']}")
    print(f"\nResume text:\n{result['resume_text']}")
