# tools/gemini_vision.py
# Wraps Gemini's native multimodal PDF understanding.
# Gemini can read BOTH typed-text PDFs and scanned/image-based PDFs
# directly — no separate OCR pipeline needed. This is what makes the
# "mixed format" exam folder tractable within our time budget.

import os
import json
from google import genai
from google.genai import types

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def identify_lecturer_and_course(pdf_bytes: bytes) -> dict:
    """
    Sends a PDF (typed or scanned) to Gemini and asks it to identify
    the lecturer's name and the course name, usually found in the header.
    """
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "Look at this exam document (it may be typed or scanned/handwritten). "
            "Identify the lecturer's name and the course name, usually found on "
            "the first page or in the header. Respond ONLY with JSON: "
            '{"lecturer_name": "...", "course_name": "..."}. '
            "If you cannot find a field, use null for that field.",
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


def extract_exam_structure(pdf_bytes: bytes) -> dict:
    """
    Sends a full exam PDF to Gemini and asks for a structured, per-question
    breakdown: topic, question type, points, and a note on phrasing style.
    """
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "Analyze this exam paper in full. For EACH question, identify: "
            "the question number, the topic/subtopic it covers, the question "
            "type (multiple_choice / open_ended / calculation / proof / "
            "short_answer), the point value if stated, and a one-line note "
            "on its phrasing style (e.g. 'derive from first principles', "
            "'application-based word problem'). "
            "Respond ONLY with JSON in this exact format: "
            '{"total_questions": N, "questions": ['
            '{"number": 1, "topic": "...", "type": "...", '
            '"points": null, "style_note": "..."}]}',
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)
