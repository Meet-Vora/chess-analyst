"""Constants and configuration settings for the AI models."""

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

DEFAULT_MODEL_ALIAS = "gemini"
DEFAULT_MODEL_FQN = resolve_model(DEFAULT_MODEL_ALIAS)
DEFAULT_EMBEDDING_MODEL = "gemini/embedding-001"

# Temperature controls the "creativity" of the LLM scale (0.0 to 1.0+). 
# Because we are asking it to act as an analytical chess coach and output strict, 
# structured JSON, we use a low temperature to prioritize analytical precision 
# and determinism over hallucination or creative writing.
ANALYSIS_TEMPERATURE = 0.2

# Slight bump in temperature for synthesis queries to allow for more varied
# and readable summaries of overall playstyle.
SYNTHESIS_TEMPERATURE = 0.3
