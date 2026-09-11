def retry_delay_seconds(attempt: int) -> int:
    """Return exponential retry delay, capped by the service safety limit."""
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    return 2 ** attempt
