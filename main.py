# main.py
# Entry point for the Exam Pattern Analyzer.
#
# Pipeline:
#   1. Validate input (regex & Pydantic sanitization)
#   2. List candidate PDF files in the public Drive folder (plain API call)
#   3. Security Agent — assesses input safety using LLM reasoning
#   4. Identifier Agent  — filters files down to the target lecturer's exams
#   5. Exam Analyzer Agent — extracts per-question structure for each
#   6. Pattern Synthesizer Agent — produces the final study report
#   7. Test Agent — performs deterministic quality assurance and validation

import os
import json
import asyncio
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from google.adk.workflow import Workflow
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from google.adk.models.llm_response import LlmResponse
from fastapi.concurrency import run_in_threadpool

from security.validators import AnalysisRequest
from tools.drive_client import find_pdfs_dfs
from security.security_agent import create_security_agent
from agents.identifier_agent import create_identifier_agent
from agents.exam_analyzer_agent import create_exam_analyzer_agent
from agents.pattern_synthesizer_agent import create_pattern_synthesizer_agent
from agents.test_agent import create_test_agent

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    raise EnvironmentError(
        "GOOGLE_API_KEY not found. Copy .env.example to .env and fill it in."
    )


def skip_if_unsafe_callback(callback_context, llm_request) -> LlmResponse | None:
    """
    Bypasses LLM model calls for downstream agents if the Security Agent
    has flagged the request as unsafe.
    """
    security_status = callback_context.state.get("security_status")
    if security_status:
        is_safe = True
        reason = None

        # Extract is_safe and reason depending on whether it's a Pydantic object or dict
        if hasattr(security_status, 'is_safe'):
            is_safe = security_status.is_safe
            reason = security_status.reason
        elif isinstance(security_status, dict):
            is_safe = security_status.get("is_safe", True)
            reason = security_status.get("reason")

        if not is_safe:
            error_json = json.dumps({
                "status": "failed",
                "error": f"Blocked by Security Agent: {reason or 'Unsafe content detected'}",
                "validation_details": {
                    "schema_check": "failed",
                    "consistency_check": "failed",
                    "warnings": ["Skipped due to security violation"]
                },
                "final_report": {}
            })
            return LlmResponse(
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text=error_json)]
                )
            )
    return None


def build_pipeline(candidate_files: list[dict] = None, target_lecturer: str = "Unknown", course_name: str = "Unknown", syllabus: str = "Unknown") -> Workflow:
    """Builds the 4-agent sequential pipeline. Each agent reads/writes shared session state."""
    security_agent = create_security_agent()

    identifier_agent = create_identifier_agent(candidate_files, target_lecturer)
    identifier_agent.before_model_callback = skip_if_unsafe_callback

    exam_analyzer_agent = create_exam_analyzer_agent()
    exam_analyzer_agent.before_model_callback = skip_if_unsafe_callback

    pattern_synthesizer_agent = create_pattern_synthesizer_agent()
    pattern_synthesizer_agent.before_model_callback = skip_if_unsafe_callback

    test_agent = create_test_agent()
    test_agent.before_model_callback = skip_if_unsafe_callback

    return Workflow(
        name="exam_pattern_pipeline",
        description=(
            "Identifies a lecturer's past exams in a Drive folder, analyzes "
            "their structure, and synthesizes study recommendations, while enforcing "
            "security and quality controls."
        ),
        edges=[
            ("START", security_agent, identifier_agent, exam_analyzer_agent, pattern_synthesizer_agent, test_agent)
        ],
    )


async def run_analysis_stream(drive_folder_url: str, lecturer_name: str, course_name: str, syllabus: str, session_id: str):
    """
    Asynchronous and streaming entry point. Validates inputs, scans Drive,
    and yields status updates and pipeline events as they occur.
    """
    # 1. Validation
    try:
        request = AnalysisRequest(
            drive_folder_url=drive_folder_url,
            lecturer_name=lecturer_name,
            course_name=course_name,
            syllabus=syllabus
        )
    except ValueError as e:
        yield {"event": "error", "data": f"Invalid input: {str(e)}"}
        return

    # 2. Drive Scan (Run in threadpool to avoid blocking the ASGI event loop)
    yield {"event": "status", "data": "Scanning Google Drive folder..."}
    logger.info(f"Scanning Drive folder: {request.drive_folder_url}")
    try:
        candidate_files = await run_in_threadpool(find_pdfs_dfs, request.drive_folder_url)
        logger.info(f"Found {len(candidate_files)} candidate PDFs.")
    except Exception as e:
        logger.error(f"Failed to list Drive files: {str(e)}")
        yield {"event": "error", "data": f"Failed to list Drive files: {str(e)}"}
        return

    if not candidate_files:
        yield {"event": "error", "data": "No PDF files found in this folder."}
        return

    yield {"event": "status", "data": f"Found {len(candidate_files)} candidate PDFs. Booting agent pipeline..."}

    # 3. Create Session (Awaited directly on the running loop)
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="exam_analyzer", user_id="student", session_id=session_id
    )

    pipeline = build_pipeline(candidate_files, request.lecturer_name, request.course_name, request.syllabus)
    runner = Runner(agent=pipeline, app_name="exam_analyzer", session_service=session_service)

    prompt = f"""
    Target lecturer: {request.lecturer_name}
    Course name: {request.course_name}
    Syllabus: {request.syllabus}
    """

    # 4. Stream events using run_async
    last_result_event = None

    try:
        async for event in runner.run_async(
            user_id="student",
            session_id=session_id,
            new_message=genai_types.Content(
                role="user", parts=[genai_types.Part(text=prompt)]
            ),
        ):
            if event.is_final_response():
                last_result_event = event
            else:
                # Emit detailed intermediate progress from tool calls
                try:
                    calls = event.get_function_calls()
                    if calls:
                        for call in calls:
                            fn_name = call.name
                            logger.info(f"Agent tool call: {fn_name}")
                            if fn_name == "check_all_files":
                                yield {"event": "progress", "data": "Identifying candidate files..."}
                            elif fn_name == "analyze_all_exams":
                                yield {"event": "progress", "data": "Extracting structures from matched exams..."}
                            elif fn_name == "verify_report_integrity":
                                yield {"event": "progress", "data": "Validating final report format..."}
                except Exception as e:
                    logger.error(f"Error parsing function calls: {e}")
                    pass
    except Exception as e:
        logger.error(f"Pipeline crashed with error: {str(e)}", exc_info=True)
        yield {"event": "error", "data": f"Pipeline crashed: {str(e)}"}
        return

    # Yield the final result after the pipeline fully completes
    if last_result_event and getattr(last_result_event, 'content', None) and last_result_event.content.parts:
        logger.info("Pipeline completed successfully. Yielding final report.")
        final_text = getattr(last_result_event.content.parts[0], 'text', '{}')
        if final_text is None:
            final_text = '{}'

        # Clean markdown code blocks
        clean_text = final_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        try:
            parsed = json.loads(clean_text)
            if isinstance(parsed, dict):
                # Unwrap ADK's output_key if present
                if "validated_report" in parsed:
                    parsed = parsed["validated_report"]
                elif "final_report" in parsed and "status" not in parsed:
                    # In case it wrapped it in final_report directly
                    parsed = parsed["final_report"]

            yield {"event": "result", "data": parsed}
        except Exception as e:
            logger.error(f"Error parsing final result: {e}")
            yield {"event": "result", "data": {"raw_output": final_text}}
