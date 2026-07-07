BANNED_WORDS = ["leverage", "utilize", "spearhead", "impactful", "synergy"]


def check_style_violations(text: str | None) -> list[str]:
    if not text:
        return []

    violations = []
    lowered = text.lower()

    for word in BANNED_WORDS:
        if word in lowered:
            violations.append(word)

    if "—" in text:
        violations.append("em dash")

    return violations


def validate_match_score(match_score: object) -> bool:
    return isinstance(match_score, (int, float)) and 0 <= match_score <= 100


def decide(match_score: float, style_violations: list[str]) -> str:
    if match_score > 65 and not style_violations:
        return "apply"
    if match_score > 65 and style_violations:
        return "flag"
    return "skip"


def evaluate(orchestrator_output: dict) -> dict:
    match_score = orchestrator_output.get("match_score")
    if not validate_match_score(match_score):
        raise ValueError(
            f"match_score must be a number between 0 and 100, got {match_score!r}"
        )

    style_violations = check_style_violations(orchestrator_output.get("tweaked_bullets"))
    decision = decide(match_score, style_violations)

    return {
        "decision": decision,
        "style_violations": style_violations,
        "match_score": match_score,
        "resume_used": orchestrator_output.get("best_resume"),
    }


if __name__ == "__main__":
    clean_output = {
        "tier": "full",
        "best_resume": "backend_resume.txt",
        "match_score": 82.5,
        "tweaked_bullets": "Built REST APIs using Python and FastAPI, cutting response times by 30 percent.",
        "recommendation": "apply",
    }

    flagged_output = {
        "tier": "full",
        "best_resume": "backend_resume.txt",
        "match_score": 78.0,
        "tweaked_bullets": "Helped leverage synergy between teams to spearhead the API rollout — fast.",
        "recommendation": "apply",
    }

    skipped_output = {
        "tier": "skip",
        "best_resume": None,
        "match_score": 24.1,
        "tweaked_bullets": None,
        "recommendation": "skip",
    }

    for label, output in [
        ("clean", clean_output),
        ("flagged", flagged_output),
        ("skipped", skipped_output),
    ]:
        result = evaluate(output)
        print(f"\n--- {label} ---")
        print(f"Decision: {result['decision']}")
        print(f"Style violations: {result['style_violations']}")
        print(f"Match score: {result['match_score']}")
        print(f"Resume used: {result['resume_used']}")
