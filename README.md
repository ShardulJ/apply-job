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
set, it returns a clearly labeled mock response instead of failing.

**backend/agents/context_assembler.py**
Ties the pieces above together. Given a job description and a list of
resumes, it picks the best resume, runs it through the screener to get a
tier, and builds a single combined context string (job description +
resume text + match metadata) that can be handed off to something like the
rewriter.

**backend/job_analyzer.py**
Placeholder for now, nothing implemented yet.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Drop resume PDFs into `backend/resumes/` (this folder is gitignored, since
resumes are personal). Set `ANTHROPIC_API_KEY` in your environment if you
want real (non-mock) output from the rewriter.

## Running things

Each module has a `__main__` block with a small self-contained example, so
you can run any of them directly to see what they do:

```bash
python backend/screener.py
python backend/agents/resume_picker.py
python backend/agents/rewriter.py
python backend/agents/context_assembler.py
```
