# agents/identifier_agent.py
# The Identifier Agent inspects each candidate PDF and decides whether it
# belongs to the target lecturer — based on the document's CONTENT, not
# its filename (since filenames are unreliable in mixed-format folders).

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config import LLM_MODEL

from tools.drive_client import download_file_bytes
from tools.gemini_vision import identify_lecturer_and_course
from security.validators import names_match


def check_lecturer_match(file_id: str, file_name: str, target_lecturer: str) -> dict:
    """
    Downloads one exam PDF and checks whether it belongs to the target lecturer.

    Args:
        file_id: Google Drive file ID of the exam PDF.
        file_name: Display name of the file (for reference in output).
        target_lecturer: The lecturer name the student is searching for.

    Returns:
        A dict with file_id, file_name, is_match (bool), and the detected
        lecturer/course names (for transparency and debugging).
    """
    pdf_bytes = download_file_bytes(file_id)
    detected = identify_lecturer_and_course(pdf_bytes)
    is_match = names_match(target_lecturer, detected.get("lecturer_name") or "")
    return {
        "file_id": file_id,
        "file_name": file_name,
        "is_match": is_match,
        "detected_lecturer": detected.get("lecturer_name"),
        "detected_course": detected.get("course_name"),
    }


def create_identifier_agent() -> LlmAgent:
    """
    Creates the Identifier Agent.

    Given a list of candidate PDF files in the Drive folder, it checks
    each one (via the check_lecturer_match tool) and filters down to only
    the exams that belong to the target lecturer.
    """
    return LlmAgent(
        name="identifier_agent",
        model=LLM_MODEL,
        description=(
            "You identify which exam files in a Drive folder belong to a "
            "specific lecturer, by inspecting the content of each PDF."
        ),
        instruction="""
        You will receive a list of candidate files (file_id + file_name)
        and a target lecturer name in the prompt.

        For EACH candidate file, call the 'check_lecturer_match' tool with
        that file's id, name, and the target lecturer name.

        After checking all files, output ONLY valid JSON listing the files
        where is_match was true:

        {
          "matched_exams": [
            {"file_id": "...", "file_name": "...", "course_name": "..."}
          ]
        }

        If no files match, return {"matched_exams": []}. Do not include
        any explanation text outside the JSON.
        """,
        tools=[FunctionTool(check_lecturer_match)],
        output_key="matched_exams",
    )
