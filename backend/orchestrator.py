import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "agents"))

from context_assembler import assemble_context
from resume_picker import pick_best_resume
from rewriter import rewrite_weak_bullets
from screener import screen_resume
from utils.token_counter import count_tokens, estimate_cost

MODEL = "claude-sonnet-5"


def _estimate_pre_call_tokens(job_description: str, resume_text: str) -> int | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    messages = [
        {
            "role": "user",
            "content": f"Job description:\n{job_description}\n\nResume:\n{resume_text}",
        }
    ]
    tokens = count_tokens(client, MODEL, messages)
    print(f"Token counter: estimated {tokens} input tokens before the Claude API call")
    return tokens


def _print_token_summary(usages: list[dict | None]) -> None:
    valid_usages = [u for u in usages if u]
    total_input_tokens = sum(u["input_tokens"] for u in valid_usages)
    total_cache_read = sum(u["cache_read_input_tokens"] for u in valid_usages)
    cost = estimate_cost(total_input_tokens)

    print("\n--- Token usage summary ---")
    print(f"Total input tokens used: {total_input_tokens}")
    print(f"Estimated cost (Sonnet, $3 per million tokens): ${cost}")
    if total_cache_read:
        print(f"Cache hits: {total_cache_read} input tokens read from cache")
    else:
        print("Cache hits: none")


def run_pipeline(job_description: str, resumes: list[dict]) -> dict:
    screen_results = [screen_resume(job_description, r["text"]) for r in resumes]
    best_screen = max(screen_results, key=lambda r: r["score"])

    if best_screen["tier"] == "skip":
        print(
            f"Skipping job: best resume match score is {best_screen['score']}, "
            "below the apply threshold"
        )
        _print_token_summary([])
        return {
            "tier": "skip",
            "best_resume": None,
            "match_score": best_screen["score"],
            "tweaked_bullets": None,
            "recommendation": "skip",
        }

    best_resume = pick_best_resume(job_description, resumes)
    context = assemble_context(job_description, resumes)

    _estimate_pre_call_tokens(job_description, best_resume["text"])
    rewrite_result = rewrite_weak_bullets(job_description, best_resume)

    _print_token_summary([rewrite_result.get("usage")])

    return {
        "tier": context["tier"],
        "best_resume": best_resume["filename"],
        "match_score": best_resume["score"],
        "tweaked_bullets": rewrite_result["rewritten_bullets"],
        "recommendation": "skip" if context["tier"] == "skip" else "apply",
    }


if __name__ == "__main__":
    sample_jd = """
    Backend Engineer role. Requirements: Python, FastAPI, REST APIs, PostgreSQL,
    Docker, CI/CD pipelines, AWS cloud platform experience.
    """

    sample_resumes = [
        {
            "filename": "backend_resume.txt",
            "text": """
            Backend Engineer, Acme Corp, 2021-2024
            - Helped build REST APIs using Python and FastAPI
            - Assisted with deploying services on AWS cloud platform
            - Set up CI/CD pipelines and managed Docker containers

            Skills: Python, FastAPI, PostgreSQL, Docker, CI/CD, AWS cloud platform
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

    result = run_pipeline(sample_jd, sample_resumes)
    print(f"\nTier: {result['tier']}")
    print(f"Best resume: {result['best_resume']}")
    print(f"Match score: {result['match_score']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Tweaked bullets:\n{result['tweaked_bullets']}")
