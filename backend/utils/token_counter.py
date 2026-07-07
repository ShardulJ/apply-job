DEFAULT_MAX_INPUT_TOKENS = 4000
SONNET_COST_PER_MILLION_TOKENS = 3.0


def count_tokens(client, model: str, messages: list, system=None) -> int:
    kwargs = {"model": model, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    result = client.messages.count_tokens(**kwargs)
    return result.input_tokens


def fit_chunks_to_budget(
    client,
    model: str,
    build_messages,
    scored_chunks: list[tuple[float, str]],
    system=None,
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
    joiner: str = "\n\n",
) -> str:
    kept = sorted(scored_chunks, key=lambda pair: pair[0], reverse=True)

    def joined(items: list[tuple[float, str]]) -> str:
        return joiner.join(text for _, text in items)

    before_tokens = count_tokens(client, model, build_messages(joined(kept)), system=system)
    print(f"Token count before truncation: {before_tokens}")

    while kept and before_tokens > max_input_tokens:
        kept.pop()
        before_tokens = count_tokens(client, model, build_messages(joined(kept)), system=system)

    after_tokens = before_tokens
    print(f"Token count after truncation: {after_tokens} (budget: {max_input_tokens})")

    return joined(kept)


def estimate_cost(input_tokens: int, cost_per_million: float = SONNET_COST_PER_MILLION_TOKENS) -> float:
    return round((input_tokens / 1_000_000) * cost_per_million, 6)


if __name__ == "__main__":
    import os

    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY to run this test block.")
    else:
        client = anthropic.Anthropic(api_key=api_key)
        model = "claude-sonnet-5"

        def build_messages(text: str) -> list:
            return [{"role": "user", "content": f"Job description: backend engineer.\n\n{text}"}]

        sample_chunks = [
            (90.0, "Built REST APIs using Python and FastAPI for five years."),
            (10.0, "Studied marine biology and coral reef ecosystems."),
            (75.0, "Deployed services on AWS with Docker and Kubernetes."),
        ]

        result_text = fit_chunks_to_budget(
            client, model, build_messages, sample_chunks, max_input_tokens=50
        )
        print(f"\nKept content:\n{result_text}")

        tokens = count_tokens(client, model, build_messages(result_text))
        cost = estimate_cost(tokens)
        print(f"\nFinal input tokens: {tokens}")
        print(f"Estimated cost: ${cost}")
