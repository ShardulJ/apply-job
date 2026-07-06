from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "all-MiniLM-L6-v2"

_model = SentenceTransformer(MODEL_NAME)


def pick_best_resume(job_description: str, resumes: list[dict]) -> dict:
    jd_embedding = _model.encode(job_description, convert_to_tensor=True)
    resume_texts = [resume["text"] for resume in resumes]
    resume_embeddings = _model.encode(resume_texts, convert_to_tensor=True)

    similarities = util.cos_sim(jd_embedding, resume_embeddings)[0]
    best_index = int(similarities.argmax())
    best_score = round(float(similarities[best_index]) * 100, 2)
    best_resume = resumes[best_index]

    return {
        "filename": best_resume["filename"],
        "score": best_score,
        "text": best_resume["text"],
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

    result = pick_best_resume(sample_jd, sample_resumes)
    print(f"Best match: {result['filename']}")
    print(f"Score: {result['score']}")
