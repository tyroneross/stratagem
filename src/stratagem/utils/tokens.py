"""Token estimation utilities — approximate cl100k_base token counts without tiktoken."""


def estimate_tokens(text: str) -> int:
    """Estimate token count for text using cl100k_base heuristics.

    Approximation rules (empirically tuned for English text):
    - ~4 characters per token for prose
    - ~3.5 characters per token for code/technical
    - Whitespace and punctuation count as partial tokens
    """
    if not text:
        return 0

    # Character-based estimation
    char_count = len(text)
    word_count = len(text.split())

    # Blend character-based and word-based estimates
    char_estimate = char_count / 4.0
    word_estimate = word_count * 1.3  # Average ~1.3 tokens per word

    # Use weighted average
    return int((char_estimate * 0.6 + word_estimate * 0.4))


def fits_context(text: str, max_tokens: int = 100_000) -> bool:
    """Check if text fits within a token budget."""
    return estimate_tokens(text) <= max_tokens


def truncate_to_tokens(text: str, max_tokens: int, suffix: str = "\n\n[...truncated]") -> str:
    """Truncate text to approximately fit within token budget."""
    if fits_context(text, max_tokens):
        return text

    # Estimate chars per token and truncate
    target_chars = int(max_tokens * 3.5)  # Conservative estimate
    if len(text) <= target_chars:
        return text

    return text[:target_chars] + suffix
