import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf_export import build_resume_filename, render_resume_fit_one_page
from screener import score_resume
from utils.token_counter import count_tokens, estimate_cost, fit_chunks_to_budget

MOCK_LABEL = "[MOCK RESPONSE - ANTHROPIC_API_KEY not set]"
TOP_N_RESUMES = 3
MAX_BULLETS_PER_JOB_SOURCE = 6
DEDUP_SIMILARITY_THRESHOLD = 0.85
MAX_INPUT_TOKENS = 4000
MODEL = "claude-sonnet-5"
FALLBACK_MODEL = "claude-sonnet-4-6"

STYLE_RULES = """
Style rules for the new resume:
- One page only, and fill the page: do not leave large empty space at the
  bottom. If content feels short, include more bullets or more detail per
  bullet rather than leaving the page sparse.
- Give each of the most recent 2-3 roles 2 to 3 bullets, and older or less
  relevant roles at least 1 bullet, unless the source material genuinely
  does not support that many.
- Most bullets should use a bold lead phrase (a concrete result or
  differentiator) followed by a colon and supporting detail, matching:
  "Built RAG pipeline: ingestion, retrieval, and grounded answer
  generation across a production system." A few plain bullets without a
  bold lead are fine too.
- No AI-sounding words like "leverage", "utilize", "spearhead", or
  "impactful"
- No dashes of any kind, anywhere, including in dates (write "Jan 2023 to
  Present", never "Jan 2023 - Present")
- Write in a human tone that passes AI detectors
- Preserve the chronological order of experiences exactly as they appear
  across the source resumes
- Quantify results wherever the source material supports it
- Lead bullets with the concrete result or differentiator, not a generic
  verb
"""

RESPONSE_FORMAT_INSTRUCTIONS = """
Respond with only a JSON object (no markdown formatting, no commentary)
with exactly these keys:
- "profile_summary": a short first person profile summary, no bullets
- "education": a list of objects with keys "degree", "school", "dates"
- "experience": a list of objects with keys "title", "company", "dates",
  and "bullets". Each bullet is either a plain string, or a two item list
  [lead, rest] where lead is a short bold differentiator phrase and rest is
  the remainder of the sentence
- "skills": a list of two item lists [category, items], where items is a
  list of individual skill strings
- "bullets_used": a list of the original bullet points, verbatim from the
  source resume content, that were selected for the new resume
"""

SECTION_HEADER_PATTERN = re.compile(r"^[A-Z][A-Z /&-]{3,}$")
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")
JOB_HEADER_SPLIT_PATTERN = re.compile(r"^(.+?)\s{2,}(.+)$")
DATE_START_PATTERN = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4})"
)

_dedup_model = None


def _get_dedup_model():
    global _dedup_model
    if _dedup_model is None:
        from sentence_transformers import SentenceTransformer

        _dedup_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _dedup_model


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def select_top_resumes(
    job_description: str, resumes: list[dict[str, str]], top_n: int = TOP_N_RESUMES
) -> list[dict[str, str]]:
    scored = [(score_resume(job_description, r["text"]), r) for r in resumes]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [resume for _, resume in scored[:top_n]]


def extract_name_and_contact(text: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else ""
    contact_line = lines[1] if len(lines) > 1 else ""
    contact_parts = [part.strip() for part in re.split(r"[|·]", contact_line) if part.strip()]
    return name, contact_parts


def extract_education_lines(text: str) -> list[str]:
    kept = []
    current_section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if SECTION_HEADER_PATTERN.match(line):
            current_section = line.upper()
            continue
        if current_section == "EDUCATION":
            kept.append(line)
    return kept


def _split_job_header(line: str) -> tuple[str, str, str]:
    match = JOB_HEADER_SPLIT_PATTERN.match(line)
    if not match:
        return line, "", ""
    title, rest = match.group(1).strip(), match.group(2).strip()
    date_match = DATE_START_PATTERN.search(rest)
    if date_match:
        company = rest[: date_match.start()].strip()
        dates = rest[date_match.start() :].strip()
    else:
        company, dates = rest, ""
    return title, company, dates


def extract_job_entries(
    text: str, max_bullets: int = MAX_BULLETS_PER_JOB_SOURCE
) -> list[dict]:
    entries: list[dict] = []
    current_section = ""
    current_entry = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if SECTION_HEADER_PATTERN.match(line):
            current_section = line.upper()
            continue

        if current_section != "EXPERIENCE":
            continue

        if line.startswith("•"):
            if current_entry is not None and len(current_entry["bullets"]) < max_bullets:
                current_entry["bullets"].append(line.lstrip("•").strip())
            continue

        if YEAR_PATTERN.search(line) or "present" in line.lower():
            title, company, dates = _split_job_header(line)
            current_entry = {"title": title, "company": company, "dates": dates, "bullets": []}
            entries.append(current_entry)

    return entries


def deduplicate_bullets(bullets: list[str], threshold: float = DEDUP_SIMILARITY_THRESHOLD) -> list[str]:
    if len(bullets) <= 1:
        return bullets

    from sentence_transformers import util

    model = _get_dedup_model()
    embeddings = model.encode(bullets, convert_to_tensor=True)

    kept_indices: list[int] = []
    for i in range(len(bullets)):
        is_duplicate = any(
            util.cos_sim(embeddings[i], embeddings[j]).item() > threshold for j in kept_indices
        )
        if not is_duplicate:
            kept_indices.append(i)

    removed = len(bullets) - len(kept_indices)
    if removed:
        print(f"Deduplicated {removed} near-duplicate bullet(s) (similarity > {threshold})")

    return [bullets[i] for i in kept_indices]


def merge_job_entries(resumes: list[dict[str, str]]) -> list[dict]:
    order: list[str] = []
    grouped: dict[str, dict] = {}

    for resume in resumes:
        for entry in extract_job_entries(resume["text"]):
            key = entry["company"] or entry["title"]
            if key not in grouped:
                grouped[key] = {
                    "title": entry["title"],
                    "company": entry["company"],
                    "dates": entry["dates"],
                    "bullets": [],
                }
                order.append(key)
            grouped[key]["bullets"].extend(entry["bullets"])

    merged = [grouped[key] for key in order]
    for entry in merged:
        entry["bullets"] = deduplicate_bullets(entry["bullets"])

    return merged


def _structured_to_plain_text(data: dict) -> str:
    lines = [data["name"], "  |  ".join(data["contact"]), "", "PROFILE SUMMARY", data["profile_summary"]]

    lines += ["", "EDUCATION"]
    for entry in data["education"]:
        lines.append(f"{entry['degree']}, {entry['school']}, {entry['dates']}")

    lines += ["", "EXPERIENCE"]
    for job in data["experience"]:
        lines.append(f"{job['title']}  {job['company']}  {job['dates']}")
        for b in job["bullets"]:
            if isinstance(b, list):
                lines.append(f"- {b[0]}: {b[1]}")
            else:
                lines.append(f"- {b}")

    lines += ["", "TECHNICAL SKILLS"]
    for category, items in data["skills"]:
        lines.append(f"{category}: {', '.join(items)}")

    return "\n".join(lines)


def _job_chunk_text(job: dict) -> str:
    bullet_lines = "\n".join(f"- {b}" for b in job["bullets"])
    return f"Job: {job['title']} at {job['company']}, {job['dates']}\nBullets:\n{bullet_lines}"


def build_tailored_resume(job_description: str, resumes: list[dict[str, str]]) -> dict:
    top_resumes = select_top_resumes(job_description, resumes)
    sources = [resume["filename"] for resume in top_resumes]
    name, contact = extract_name_and_contact(top_resumes[0]["text"])

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "name": name,
            "contact": contact,
            "resume_text": f"{MOCK_LABEL}\nSet ANTHROPIC_API_KEY to generate a real tailored resume.",
            "bullets_used": [],
            "sources": sources,
            "mock": True,
            "usage": None,
        }

    try:
        import anthropic
    except ImportError:
        return {
            "name": name,
            "contact": contact,
            "resume_text": f"{MOCK_LABEL}\nThe anthropic package is not installed.",
            "bullets_used": [],
            "sources": sources,
            "mock": True,
            "usage": None,
        }

    merged_jobs = merge_job_entries(top_resumes)
    education_lines = extract_education_lines(top_resumes[0]["text"])

    job_chunks = [
        (score_resume(job_description, "\n".join(job["bullets"])), _job_chunk_text(job))
        for job in merged_jobs
        if job["bullets"]
    ]

    client = anthropic.Anthropic(api_key=api_key)

    system_blocks = [
        {
            "type": "text",
            "text": STYLE_RULES + RESPONSE_FORMAT_INSTRUCTIONS,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    def build_messages(job_content: str) -> list:
        prompt = f"""Job description:
{job_description}

Education (verbatim, use as is):
{chr(10).join(education_lines)}

Candidate experience, grouped by role, bullets already deduplicated:
{job_content}

Read the experience above and construct one new tailored resume using the
most relevant bullets for this specific job."""
        return [{"role": "user", "content": prompt}]

    final_job_content = fit_chunks_to_budget(
        client,
        MODEL,
        build_messages,
        job_chunks,
        system=system_blocks,
        max_input_tokens=MAX_INPUT_TOKENS,
    )

    messages = build_messages(final_job_content)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system_blocks,
            thinking={"type": "disabled"},
            messages=messages,
        )
    except anthropic.BadRequestError:
        response = client.messages.create(
            model=FALLBACK_MODEL,
            max_tokens=4000,
            system=[{"type": "text", "text": STYLE_RULES + RESPONSE_FORMAT_INSTRUCTIONS}],
            messages=messages,
        )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        raise ValueError("No text block in API response")

    result = json.loads(_strip_code_fence(text_blocks[0]))

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    }

    structured = {
        "name": name,
        "contact": contact,
        "profile_summary": result["profile_summary"],
        "education": result["education"],
        "experience": result["experience"],
        "skills": result["skills"],
    }

    return {
        "name": name,
        "contact": contact,
        "profile_summary": result["profile_summary"],
        "education": result["education"],
        "experience": result["experience"],
        "skills": result["skills"],
        "resume_text": _structured_to_plain_text(structured),
        "bullets_used": result["bullets_used"],
        "sources": sources,
        "mock": False,
        "usage": usage,
    }


def save_tailored_resume_pdf(
    job_description: str, resumes: list[dict[str, str]], company: str, job_title: str
) -> dict:
    result = build_tailored_resume(job_description, resumes)
    output_path = build_resume_filename(company, job_title)

    if result["mock"]:
        result["pdf_path"] = None
        return result

    fits_one_page = render_resume_fit_one_page(result, output_path)
    result["pdf_path"] = output_path
    result["fits_one_page"] = fits_one_page
    return result


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
            JANE DOE
            Boston, MA | jane@example.com
            PROFILE SUMMARY
            Senior ML engineer with 5 years building production ML systems.
            EDUCATION
            MS Computer Science, DePaul University, 2023-2025
            EXPERIENCE
            ML Engineer   Acme AI Jan 2023 – Present
            •Built RAG pipelines for enterprise document search
            •Designed evaluation frameworks to measure retrieval quality
            •Deployed backend APIs on AWS serving low-latency inference
            Data Analyst   Acme AI Jun 2021 – Jan 2023
            •Built dashboards for internal reporting
            TECHNICAL SKILLS
            Python, PyTorch, AWS, Docker, FastAPI
            """,
        },
        {
            "filename": "resume_b.txt",
            "text": """
            JANE DOE
            Boston, MA | jane@example.com
            PROFILE SUMMARY
            ML engineer with experience in NLP and data pipelines.
            EDUCATION
            MS Computer Science, DePaul University, 2023-2025
            EXPERIENCE
            ML Engineer   Acme AI Jan 2023 – Present
            •Built retrieval augmented generation pipelines for document search
            •Created evaluation harnesses to measure retrieval accuracy
            Data Scientist   Beta Corp Mar 2021 – Jan 2023
            •Built classification models for customer support tickets
            •Automated data pipelines using Airflow
            TECHNICAL SKILLS
            Python, SQL, Airflow, scikit-learn
            """,
        },
        {
            "filename": "resume_c.txt",
            "text": """
            JANE DOE
            Boston, MA | jane@example.com
            PROFILE SUMMARY
            Frontend developer specializing in React and design systems.
            EDUCATION
            BS Design, Art University, 2018-2022
            EXPERIENCE
            Frontend Developer   Pixel Studio Jun 2022 – Jun 2024
            •Built responsive UIs using React and TypeScript
            •Designed component libraries and CSS frameworks
            TECHNICAL SKILLS
            React, TypeScript, CSS, Figma
            """,
        },
        {
            "filename": "resume_d.txt",
            "text": """
            JANE DOE
            Boston, MA | jane@example.com
            PROFILE SUMMARY
            Marine biologist studying coral reef ecosystems.
            EDUCATION
            PhD Marine Biology, Ocean University, 2015-2020
            EXPERIENCE
            Research Scientist   Ocean Institute Jun 2020 – Jun 2024
            •Conducted scuba diving field research on coral reefs
            •Analyzed ocean temperature data using statistical models
            TECHNICAL SKILLS
            R, GIS, Field Research, Data Analysis
            """,
        },
    ]

    result = save_tailored_resume_pdf(
        sample_jd, sample_resumes, company="Acme Corp", job_title="Senior ML Engineer"
    )
    print(f"Mock: {result['mock']}")
    print(f"Sources (top {TOP_N_RESUMES} by TF-IDF score): {result['sources']}")
    print(f"PDF saved to: {result['pdf_path']}")
    if result["usage"]:
        usage = result["usage"]
        cost = estimate_cost(usage["input_tokens"])
        print(f"Usage: {usage}")
        print(f"Estimated cost: ${cost}")
    print(f"\nBullets used:\n{result['bullets_used']}")
