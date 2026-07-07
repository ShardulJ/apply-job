import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.token_counter import count_tokens

MOCK_LABEL = "[MOCK RESPONSE - ANTHROPIC_API_KEY not set]"
FALLBACK_MODEL = "claude-sonnet-4-6"

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
) -> dict:
    filename = resume["filename"]
    resume_text = resume["text"]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "filename": filename,
            "rewritten_bullets": f"{MOCK_LABEL}\nSet ANTHROPIC_API_KEY to generate a real rewrite.",
            "mock": True,
            "usage": None,
        }

    try:
        import anthropic
    except ImportError:
        return {
            "filename": filename,
            "rewritten_bullets": f"{MOCK_LABEL}\nThe anthropic package is not installed.",
            "mock": True,
            "usage": None,
        }

    client = anthropic.Anthropic(api_key=api_key)

    system_blocks = [
        {
            "type": "text",
            "text": STYLE_RULES,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    prompt = f"""Job description:
{job_description}

Resume ({filename}):
{resume_text}

Identify the 2-3 weakest bullet points in this resume relative to the job description
above, and rewrite only those bullet points so they better match the job.

Return only the rewritten bullet points, one per line. Do not return the full resume
and do not add any commentary."""

    messages = [{"role": "user", "content": prompt}]

    before_tokens = count_tokens(client, model, messages, system=system_blocks)
    print(f"Token count before call: {before_tokens}")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            system=system_blocks,
            thinking={"type": "disabled"},
            messages=messages,
        )
    except anthropic.BadRequestError:
        response = client.messages.create(
            model=FALLBACK_MODEL,
            max_tokens=500,
            system=[{"type": "text", "text": STYLE_RULES}],
            messages=messages,
        )

    rewritten_bullets = next(
        block.text for block in response.content if block.type == "text"
    ).strip()

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    }
    print(
        f"Token count after call: {usage['input_tokens']} input, "
        f"{usage['cache_read_input_tokens']} from cache"
    )

    return {
        "filename": filename,
        "rewritten_bullets": rewritten_bullets,
        "mock": False,
        "usage": usage,
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
