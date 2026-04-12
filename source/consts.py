"""Constants and configuration settings for the Chess Analyst application."""

MODEL_ALIASES = {
    "gemini": "gemini/gemini-2.5-flash",
    "gemini-flash": "gemini/gemini-2.5-flash",
    "gemini-pro": "gemini/gemini-2.5-pro",
    "claude": "anthropic/claude-3-5-sonnet-latest",
    "claude-sonnet": "anthropic/claude-3-5-sonnet-latest",
    "gpt": "openai/gpt-4o",
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "grok": "xai/grok-2-latest",
}

def resolve_model(model_str: str) -> str:
    """Returns the litellm fully qualified model string for an alias, or the string itself."""
    return MODEL_ALIASES.get(model_str.lower(), model_str)
