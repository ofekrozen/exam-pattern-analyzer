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
import logging

logger = logging.getLogger(__name__)


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
    try:
        logger.info(f"Downloading file for matching: {file_name}")
        pdf_bytes = download_file_bytes(file_id)
        detected = identify_lecturer_and_course(pdf_bytes)
        logger.info(f"Detected via Vision: lecturer={detected.get('lecturer_name')}, course={detected.get('course_name')}")
        is_match = names_match(target_lecturer, detected.get("lecturer_name") or "")
        logger.info(f"Match result for {file_name}: {is_match}")
        return {
            "file_id": file_id,
            "file_name": file_name,
            "is_match": is_match,
            "detected_lecturer": detected.get("lecturer_name"),
            "detected_course": detected.get("course_name"),
        }
    except Exception as e:
        logger.error(f"Error checking match for {file_name}: {str(e)}", exc_info=True)
        return {
            "file_id": file_id,
            "file_name": file_name,
            "is_match": False,
            "error": str(e)
        }

_tool_cache = []

def create_identifier_agent(candidate_files: list[dict] = None, target_lecturer: str = "Unknown") -> LlmAgent:
    from agents.schemas import IdentifierOutput
    import json
    from collections import defaultdict

    def check_all_files() -> str:
        """
        Executes the content match checking on all candidate files.
        Takes no parameters. It automatically processes all candidate files.
        """
        if _tool_cache:
            logger.info("Returning cached files to prevent duplicate tool execution.")
            return _tool_cache[0]

        files = candidate_files or []
        groups = defaultdict(list)
        for f in files:
            pid = f.get("parent_id", "unknown")
            groups[pid].append(f)

        results = []
        for pid, group_files in groups.items():
            group_match = False
            for f in group_files:
                match_result = check_lecturer_match(f.get("id", ""), f.get("name", ""), target_lecturer)
                if match_result.get("is_match"):
                    group_match = True
                    break

            logger.info(f"Group match status for parent_id {pid}: {group_match}")
            for f in group_files:
                results.append({
                    "file_id": f.get("id", ""),
                    "file_name": f.get("name", ""),
                    "is_match": group_match,
                    "reason": "Group match inference" if group_match else "No match found in folder"
                })

        logger.info(f"Total matched files returned to LLM: {sum(1 for r in results if r['is_match'])}")
        res = json.dumps(results)
        _tool_cache.append(res)
        return res

    return LlmAgent(
        name="identifier_agent",
        model=LLM_MODEL,
        description=(
            "You identify which exam files in a Drive folder belong to a "
            "specific lecturer, by inspecting the content of each PDF."
        ),
        instruction=f"""
        CRITICAL INSTRUCTIONS:
        Step 1: You MUST execute the 'check_all_files' tool EXACTLY ONCE to get the match results. It takes NO parameters.
        Step 2: Wait for the tool to return the result array. Do NOT guess the matches yourself.
        Step 3: After the tool returns, you must output a JSON object listing only the files where 'is_match' was true.

        Use this exact JSON output format:
        {{
          "matched_exams": [
            {{"file_id": "...", "file_name": "...", "course_name": "..."}}
          ]
        }}
        """,
        tools=[FunctionTool(check_all_files)],
        output_schema=IdentifierOutput,
        output_key="matched_exams",
    )
