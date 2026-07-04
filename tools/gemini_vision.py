# tools/gemini_vision.py
# Wraps Gemini's native multimodal PDF understanding.
# Gemini can read BOTH typed-text PDFs and scanned/image-based PDFs
# directly — no separate OCR pipeline needed. This is what makes the
# "mixed format" exam folder tractable within our time budget.

import os
import json
from google import genai
from google.genai import types
from config import VISION_MODEL

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
    Sends a PDF to Gemini to evaluate the document and extract the lecturer's name.
    """
    client = _get_client()
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "Look at this document (it may be typed or scanned/handwritten). "
            "Extract the lecturer's name and the course name, usually found in the header or first page. "
            "IMPORTANT: Extract the names EXACTLY in the original language of the document. "
            "Respond ONLY with JSON using this structure: "
            '{"lecturer_name": "...", "course_name": "..."}'
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


def extract_exam_structure(pdf_bytes: bytes, course_name: str, syllabus: str) -> dict:
    """
    Extracts the full question structure or student solutions from a PDF.
    """
    client = _get_client()
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            f"Identify the document type: 'exam' (a blank test) or 'student_solution' (a filled-in test with grades/comments) or 'unknown'. "
            f"The course is '{course_name}' and the syllabus is: '{syllabus}'. "
            "If document type is 'exam': "
            "For EACH question, identify: the question number, "
            "and classify the question with 1-3 tags based on the topics mentioned in the syllabus. "
            "Also include the question type (multiple_choice / open_ended / calculation / proof / short_answer). "
            "If document type is 'student_solution': "
            "Identify the student's mistakes, and what the lecturer lowered the score on. "
            "Respond ONLY with JSON. Ensure the JSON is properly formatted. "
            "Use this structure if the document is an exam (blank test): "
            '{"document_type": "exam", "total_questions": N, "questions": [{"q_number": 1, "tags": ["..."], "type": "..."}]} '
            "Use this structure if the document is a student_solution (filled-in test with grades): "
            '{"document_type": "student_solution", "score_deductions": [{"q_number": 1, "mistake": "...", "deduction_reason": "..."}]} '
            "Use this structure if unknown: "
            '{"document_type": "unknown"}'
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)
