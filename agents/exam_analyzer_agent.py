# agents/exam_analyzer_agent.py
# The Exam Analyzer Agent takes the matched exams (from the Identifier
# Agent) and extracts a detailed, per-question breakdown of each one.

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config import LLM_MODEL

from tools.drive_client import download_file_bytes
from tools.gemini_vision import extract_exam_structure
import logging

logger = logging.getLogger(__name__)


def analyze_exam(file_id: str, file_name: str, course_name: str, syllabus: str) -> dict:
    """
    Downloads one matched exam and extracts its full question structure.

    Args:
        file_id: Google Drive file ID of the exam.
        file_name: Display name of the exam (used to label the output).
        course_name: Name of the course.
        syllabus: Course syllabus.

    Returns:
        A dict with file_name, total_questions, and the per-question
        breakdown (q_number, q_content, tags, type).
    """
    try:
        logger.info(f"Downloading matched exam for analysis: {file_name}")
        pdf_bytes = download_file_bytes(file_id)
        structure = extract_exam_structure(pdf_bytes, course_name, syllabus)
        logger.info(f"Successfully extracted {structure.get('total_questions', 0)} questions from {file_name}")
        return {"file_name": file_name, **structure}
    except Exception as e:
        logger.error(f"Error extracting structure for {file_name}: {str(e)}", exc_info=True)
        return {"file_name": file_name, "total_questions": 0, "questions": [], "error": str(e)}

def analyze_all_exams(matched_exams_json_string: str, course_name: str, syllabus: str) -> str:
    import json
    try:
        data = json.loads(matched_exams_json_string)
        if isinstance(data, dict) and "matched_exams" in data:
            exams = data["matched_exams"]
        elif isinstance(data, list):
            exams = data
        else:
            exams = []
    except:
        return "Error: Invalid JSON string provided."

    results = []
    logger.info(f"Analyzing {len(exams)} matched exams...")
    for ex in exams:
        if isinstance(ex, dict):
            results.append(analyze_exam(ex.get("file_id", ""), ex.get("file_name", ""), course_name, syllabus))

    logger.info("Finished analyzing all matched exams.")
    return json.dumps(results)


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
        You also have the course_name and syllabus in the system prompt.

        CRITICAL INSTRUCTIONS:
        Step 1: You MUST execute the 'analyze_all_exams' tool EXACTLY ONCE. Pass the raw JSON string of matched_exams as 'matched_exams_json_string', along with the course_name and syllabus.
        Step 2: Wait for the tool to return the parsed question structures. Do NOT generate the response until the tool returns!
        Step 3: Output the results exactly as returned by the tool.

        Use this exact JSON output format:
        {
          "exams": [
            {"file_name": "...", "total_questions": N, "questions": [...]}
          ]
        }
        """,
        tools=[FunctionTool(analyze_all_exams)],
        output_key="exam_analyses",
    )
