# agents/exam_analyzer_agent.py
# The Exam Analyzer Agent takes the matched exams (from the Identifier
# Agent) and extracts a detailed, per-question breakdown of each one.

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config import LLM_MODEL

from tools.drive_client import download_file_bytes
from tools.gemini_vision import extract_exam_structure


def analyze_exam(file_id: str, file_name: str) -> dict:
    """
    Downloads one matched exam and extracts its full question structure.

    Args:
        file_id: Google Drive file ID of the exam.
        file_name: Display name of the exam (used to label the output).

    Returns:
        A dict with file_name, total_questions, and the per-question
        breakdown (topic, type, points, style note).
    """
    pdf_bytes = download_file_bytes(file_id)
    structure = extract_exam_structure(pdf_bytes)
    return {"file_name": file_name, **structure}


def create_exam_analyzer_agent() -> LlmAgent:
    """
    Creates the Exam Analyzer Agent.

    Takes 'matched_exams' from session state and extracts a full
    per-question breakdown for each one using the 'analyze_exam' tool.
    """
    return LlmAgent(
        name="exam_analyzer_agent",
        model=LLM_MODEL,
        description=(
            "You extract the detailed structure (questions, topics, types) "
            "of each matched exam PDF."
        ),
        instruction="""
        You will receive 'matched_exams' from session state — a list of
        {file_id, file_name, course_name} for exams already confirmed to
        belong to the target lecturer.

        For EACH exam in that list, call the 'analyze_exam' tool to get
        its full question structure.

        Output ONLY valid JSON:
        {
          "exams": [
            {"file_name": "...", "total_questions": N, "questions": [...]}
          ]
        }

        Do not include any explanation text outside the JSON.
        """,
        tools=[FunctionTool(analyze_exam)],
        output_key="exam_analyses",
    )
