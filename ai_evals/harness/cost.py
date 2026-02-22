import tiktoken

# per-1K-token cost for GPT-4o-mini (example)
PRICE_PER_1K = 0.003  # USD

def calculate_cost(text: str, model: str = "gpt-4o-mini") -> float:
    """ Estimates the API cost in USD for a given text payload. """
    encoder = tiktoken.encoding_for_model(model)
    tokens = len(encoder.encode(text))
    return (tokens / 1000) * PRICE_PER_1K

# Example
prompt = "Who founded PostgreSQL?"
print(f"Cost: ${calculate_cost(prompt):.6f}")  # → e.g. $0.000090