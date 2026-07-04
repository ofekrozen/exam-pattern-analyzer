# agents/document_processing_agent.py
# The Document Processing Agent takes the candidate PDFs, and in a SINGLE pass,
# checks if they belong to the lecturer and extracts the exam questions if they do.

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config import LLM_MODEL
import logging

logger = logging.getLogger(__name__)

from tools.drive_client import download_file_bytes
from tools.gemini_vision import process_exam_document

def create_document_processing_agent(candidate_files: list[dict] = None, target_lecturer: str = "Unknown", course_name: str = "Unknown", syllabus: str = "Unknown") -> LlmAgent:
    import json
    from collections import defaultdict
    from agents.schemas import DocumentProcessingOutput

    # Cache the result to prevent the LLM from looping and re-downloading files on validation retries
    _tool_cache = []

    def process_all_files() -> str:
        """Processes all candidate PDF files in Google Drive to extract exams and solutions."""
        if _tool_cache:
            logger.info("Returning cached files to prevent duplicate tool execution.")
            return _tool_cache[0]

        files = candidate_files or []
        groups = defaultdict(list)
        for f in files:
            pid = f.get("parent_id", "unknown")
            groups[pid].append(f)

        results = []
        import concurrent.futures
        MAX_EXAMS = 5
        MAX_SOLUTIONS = 5
        exams_found = 0
        solutions_found = 0

        def process_single_file(f, is_force_analyze=False):
            file_name = f.get("name", "")
            file_id = f.get("id", "")
            try:
                logger.info(f"Downloading and processing: {file_name} (force_analyze={is_force_analyze})")
                pdf_bytes = download_file_bytes(file_id)
                detected = process_exam_document(pdf_bytes, target_lecturer, course_name, syllabus, force_analyze=is_force_analyze)
                logger.info(f"Detected via Vision: lecturer={detected.get('lecturer_name')}, is_target={detected.get('is_target_lecturer')}")
                return {"file_name": file_name, "id": file_id, "success": True, "detected": detected}
            except Exception as e:
                logger.error(f"Error processing {file_name}: {str(e)}", exc_info=True)
                return {"file_name": file_name, "id": file_id, "success": False}

        for pid, group_files in groups.items():
            if exams_found >= MAX_EXAMS and solutions_found >= MAX_SOLUTIONS:
                break

            group_match = False
            results_for_group = []
            checked_but_no_match = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_file = {executor.submit(process_single_file, f, False): f for f in group_files}
                for future in concurrent.futures.as_completed(future_to_file):
                    res = future.result()
                    if not res.get("success"): continue

                    detected = res["detected"]
                    if detected.get("is_target_lecturer"):
                        group_match = True
                        results_for_group.append(res)
                    else:
                        checked_but_no_match.append(res)

            if group_match:
                logger.info(f"Group match confirmed for folder {pid}. Re-extracting missed files with force_analyze=True...")
                missed_files = [{"name": r["file_name"], "id": r["id"]} for r in checked_but_no_match]
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_missed = {executor.submit(process_single_file, f, True): f for f in missed_files}
                    for future in concurrent.futures.as_completed(future_to_missed):
                        res = future.result()
                        if res.get("success"):
                            results_for_group.append(res)

            for r in results_for_group:
                detected = r["detected"]
                dtype = detected.get("document_type")
                if dtype == "exam" and exams_found < MAX_EXAMS:
                    results.append({"file_name": r["file_name"], **detected})
                    exams_found += 1
                elif dtype == "student_solution" and solutions_found < MAX_SOLUTIONS:
                    results.append({"file_name": r["file_name"], **detected})
                    solutions_found += 1

        output_dict = {"exams": [], "student_solutions": []}
        for item in results:
            dtype = item.get("document_type")
            if dtype == "exam":
                output_dict["exams"].append(item)
            elif dtype == "student_solution":
                output_dict["student_solutions"].append(item)

        logger.info(f"Total analyzed exams returned to LLM: {len(output_dict['exams'])}, solutions: {len(output_dict['student_solutions'])}")
        res_json = json.dumps(output_dict)
        _tool_cache.append(res_json)
        return res_json

    agent = LlmAgent(
        name="document_processing_agent",
        model=LLM_MODEL,
        description=(
            "You identify which exam files in a Drive folder belong to the "
            "target lecturer, and extract their full structural breakdown."
        ),
        instruction="Bypassed by native callback.",
        tools=[],  # No tools needed since we bypass the LLM entirely
        output_schema=DocumentProcessingOutput,
        output_key="exam_analyses",
    )

    def manual_execution_callback(callback_context, llm_request):
        logger.info("Bypassing LLM API to process files natively...")
        res_json = process_all_files()

        # We need to return an LlmResponse mimicking the model's output
        from google.genai import types as genai_types
        from google.adk.models.llm_response import LlmResponse
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=res_json)]
            )
        )

    agent.before_model_callback = manual_execution_callback
    return agent
