import os
from dotenv import load_dotenv

# Load .env from Lumina project root (two levels up from this file)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


def get_api_key() -> str:
    """Returns the Gemini API key from environment."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Please add it to your .env file in the Lumina project root."
        )
    return key


def get_genai_model(model_name: str = "gemini-2.5-flash"):
    """
    Returns a configured google.generativeai GenerativeModel instance.
    Uses the older `google.generativeai` SDK (compatible with Mark-XXX actions).
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=get_api_key())
        return genai.GenerativeModel(model_name)
    except ImportError:
        raise RuntimeError(
            "google-generativeai is not installed. "
            "Run: pip install google-generativeai"
        )


def get_genai_client():
    """
    Returns a configured google.genai Client instance.
    Uses the newer `google.genai` SDK (matching Lumina's own pattern).
    """
    try:
        from google import genai
        return genai.Client(api_key=get_api_key())
    except ImportError:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        )
