import os
from dotenv import load_dotenv

load_dotenv()

# Model used by all ADK LLM agents.
# Switch to "openai/gpt-4o-mini" (and set OPENAI_API_KEY) when
# Gemini free-tier quota is exhausted.
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-lite")

# Model used by gemini_vision.py for native PDF reading.
# Must stay on a Gemini model — OpenAI does not support raw PDF bytes.
# Requires GOOGLE_API_KEY regardless of LLM_MODEL above.
VISION_MODEL = os.getenv("VISION_MODEL", "gemini-2.0-flash-lite")
