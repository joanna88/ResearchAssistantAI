from google.adk.models import Gemini
from google.genai import types

MODEL_NAME = "gemini-3.5-flash-lite"


def make_model() -> Gemini:
    """Gemini model with retries on temporary errors (shared by all agents)."""

    return Gemini(
        model=MODEL_NAME,
        retry_options=types.HttpRetryOptions(
            initial_delay=1, attempts=5, http_status_codes=[429, 500, 503, 504]
        ),
    )
