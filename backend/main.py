import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "eval"))

from evaluator import evaluate
from logger import log_application
from orchestrator import run_pipeline
from resume_parser import load_all_resumes

resumes: list[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global resumes
    resumes = load_all_resumes()
    print(f"Server running. Loaded {len(resumes)} resumes.")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    job_description: str
    company: str
    job_title: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    pipeline_result = run_pipeline(request.job_description, resumes)
    eval_result = evaluate(pipeline_result)

    log_application(
        company=request.company,
        job_title=request.job_title,
        resume_used=eval_result["resume_used"],
        match_score=eval_result["match_score"],
        tier=pipeline_result["tier"],
        decision=eval_result["decision"],
        style_violations=eval_result["style_violations"],
    )

    return {
        "tier": pipeline_result["tier"],
        "best_resume": pipeline_result["best_resume"],
        "match_score": pipeline_result["match_score"],
        "tweaked_bullets": pipeline_result["tweaked_bullets"],
        "decision": eval_result["decision"],
        "style_violations": eval_result["style_violations"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
