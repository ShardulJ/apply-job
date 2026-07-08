# apply-job

A small toolkit for matching resumes against job descriptions and helping
tailor a resume to a specific job. This is a work in progress, built up one
piece at a time.

## What's here so far

**backend/resume_parser.py**
Loads resumes from `backend/resumes/` (PDF files) and extracts their text
using PyPDF2, so the rest of the pipeline has plain text to work with.

**backend/screener.py**
A quick pre-screen that compares a job description against a resume using
TF-IDF and cosine similarity (scikit-learn). It returns a 0-100 score and
buckets it into a tier: `skip` (under 50), `partial` (50-70), or `full`
(above 70). This is meant to be a cheap first pass before doing anything
more expensive.

**backend/agents/resume_picker.py**
Given a job description and a list of resumes, picks the single best match
using sentence embeddings (`all-MiniLM-L6-v2` from sentence-transformers)
and cosine similarity. Unlike the screener, this compares meaning rather
than word overlap, so it's better at picking the right resume out of a
pile.

**backend/agents/rewriter.py**
Takes a job description and a resume and calls the Claude API to rewrite
the 2-3 weakest bullet points so they better match the job. The rewrite is
guided by a set of style rules: no AI-sounding words like "leverage" or
"utilize", no em dashes, no weak verbs like "helped" or "assisted",
chronological order stays untouched, skills stay comma separated, and the
result should read like a person wrote it. If `ANTHROPIC_API_KEY` isn't
set, it returns a clearly labeled mock response instead of failing. Style
rules are sent as a cached system prompt (Anthropic prompt caching) and
every call logs its token count before and after, via
`backend/utils/token_counter.py`.

**backend/agents/resume_builder.py**
Given a job description and the full list of resumes, builds a brand new
tailored one-page resume instead of just tweaking a few bullets. It
TF-IDF-screens down to the top 3 most relevant resumes, pulls each one's
experience apart into per-job bullet groups, semantically deduplicates
near-identical bullets across resume versions (sentence-transformers
embeddings, drops anything over 0.85 cosine similarity to a bullet already
kept), fits the remaining content to a 4000 input token budget by trimming
the least relevant job chunks first, then makes one cached Claude call to
produce structured JSON (profile summary, education, experience, skills).
Name and contact info are pulled directly off the top resume rather than
regenerated, since that's factual data an LLM shouldn't paraphrase.

**backend/pdf_export.py**
Renders a structured resume (the shape `resume_builder.py` produces) into
a PDF matching a specific one-page layout: Arial throughout, a bordered
section header style, bold-lead bullets, right-aligned dates, reverse
chronological experience, comma-separated skills. `render_resume_fit_one_page`
is the version actually used in practice: if the content overflows one
page, it trims bullets from the longest experience entries and re-renders
until it fits, rather than shrinking fonts or spilling to page 2. Output
files are named `Resume_{Company}_{JobTitle}_{Date}.pdf` in
`backend/output/`.

**backend/utils/token_counter.py**
Shared helper used by the agents above. Wraps the Anthropic client's
`count_tokens` call, and `fit_chunks_to_budget` takes a list of
(relevance score, text) chunks and drops the lowest-scored ones until the
whole prompt fits under a token budget, logging the before and after
counts.

**backend/agents/context_assembler.py**
Ties the pieces above together. Given a job description and a list of
resumes, it picks the best resume, runs it through the screener to get a
tier, and builds a single combined context string (job description +
resume text + match metadata) that can be handed off to something like the
rewriter.

**backend/orchestrator.py**
Wires everything above into one pipeline. `run_pipeline(job_description,
resumes)` runs a cheap TF-IDF screen across all resumes first, and if the
best score comes back as a skip tier, it logs why and returns early
without touching the embedding model or the Claude API. Otherwise it picks
the best resume, assembles context, estimates the token count before
calling Claude, and rewrites the weak bullets, then returns a single dict
with `tier`, `best_resume`, `match_score`, `tweaked_bullets`, and a final
`recommendation` of `apply` or `skip`. Every run ends with a token usage
summary: total input tokens, estimated cost at Sonnet's $3 per million
rate, and any cache hits.

**backend/eval/evaluator.py**
Checks the orchestrator's output before anything gets sent out. It scans
the tweaked bullets for banned resume-speak (leverage, utilize, spearhead,
impactful, synergy) and em dashes, confirms the match score is a real
number between 0 and 100, and gates a final decision: `apply` if the score
is above 65 with no style violations, `flag` if the score is above 65 but
the wording needs cleanup, or `skip` if the score is too low.

**backend/logger.py**
Appends one row per application to `backend/output/applications_log.csv`
(timestamp, company, job title, resume used, match score, tier, decision,
style violations), writing the header row the first time the file is
created.

**backend/main.py**
A FastAPI app that ties the whole pipeline together. `POST /analyze` takes
a job description, company, and job title, runs it through the
orchestrator and evaluator, logs the outcome to CSV, and returns the full
result as JSON. `GET /health` is a plain liveness check. CORS is wide open
since this is meant to be called from a browser extension, and the
`ANTHROPIC_API_KEY` is loaded from a local `.env` file on startup.

**backend/job_analyzer.py**
Placeholder for now, nothing implemented yet.

**extension/**
A Chrome extension (Manifest V3) that scrapes the job posting on the
current tab and sends it to the backend for analysis. `content.js` reads
the page (LinkedIn, Greenhouse, or Lever), `popup.js` sends that to
`POST http://localhost:8000/analyze` and renders the score, decision,
tweaked bullets, and style violations. See `extension/README.md` for how
to load it in Chrome.

**Known issue:** scraping currently fails with "Could not read this page"
on at least LinkedIn. The content script isn't reliably reaching the
page, likely a stale-tab or selector mismatch issue rather than the
backend itself. Not yet fixed.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Drop resume PDFs into `backend/resumes/` (this folder is gitignored, since
resumes are personal). Create a `backend/.env` file with
`ANTHROPIC_API_KEY=your-key-here` if you want real (non-mock) output from
the rewriter; `.env` is gitignored too, so it never leaves your machine.

## Running things

Each module has a `__main__` block with a small self-contained example, so
you can run any of them directly to see what they do:

```bash
python backend/screener.py
python backend/agents/resume_picker.py
python backend/agents/rewriter.py
python backend/agents/resume_builder.py
python backend/agents/context_assembler.py
python backend/orchestrator.py
python backend/eval/evaluator.py
python backend/logger.py
python backend/pdf_export.py
python backend/utils/token_counter.py
```

To run the API server itself:

```bash
python backend/main.py
```

Then hit it directly:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"job_description": "...", "company": "Acme Corp", "job_title": "Backend Engineer"}'
```
