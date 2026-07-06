from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def score_resume(job_description: str, resume_text: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([job_description, resume_text])
    similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
    return round(similarity * 100, 2)


def get_tier(score: float) -> str:
    if score < 50:
        return "skip"
    if score <= 70:
        return "partial"
    return "full"


def screen_resume(job_description: str, resume_text: str) -> dict[str, float | str]:
    score = score_resume(job_description, resume_text)
    tier = get_tier(score)
    return {"score": score, "tier": tier}


if __name__ == "__main__":
    sample_jd = """
    We are looking for a Backend Engineer with strong experience in Python,
    FastAPI, REST APIs, and relational databases such as PostgreSQL. Experience
    with Docker, CI/CD pipelines, and cloud platforms like AWS is a plus.
    """

    sample_resume = """
    Backend developer with 4 years of experience building REST APIs using
    Python and FastAPI. Skilled in PostgreSQL, Docker, and deploying services
    on AWS. Familiar with setting up CI/CD pipelines using GitHub Actions.
    """

    result = screen_resume(sample_jd, sample_resume)
    print(f"Score: {result['score']}")
    print(f"Tier: {result['tier']}")
