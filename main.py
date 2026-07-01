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
from dotenv import load_dotenv

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


def build_pipeline() -> Workflow:
    """Builds the 5-agent sequential pipeline. Each agent reads/writes shared session state."""
    security_agent = create_security_agent()

    identifier_agent = create_identifier_agent()
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


async def run_analysis_stream(drive_folder_url: str, lecturer_name: str, session_id: str):
    """
    Asynchronous and streaming entry point. Validates inputs, scans Drive,
    and yields status updates and pipeline events as they occur.
    """
    # 1. Validation
    try:
        request = AnalysisRequest(drive_folder_url=drive_folder_url, lecturer_name=lecturer_name)
    except ValueError as e:
        yield {"event": "error", "data": f"Invalid input: {str(e)}"}
        return

    # 2. Drive Scan (Run in threadpool to avoid blocking the ASGI event loop)
    yield {"event": "status", "data": "Scanning Google Drive folder..."}
    try:
        candidate_files = await run_in_threadpool(find_pdfs_dfs, request.drive_folder_url)
    except Exception as e:
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

    pipeline = build_pipeline()
    runner = Runner(agent=pipeline, app_name="exam_analyzer", session_service=session_service)

    prompt = f"""
    Target lecturer: {request.lecturer_name}

    Candidate exam files in the folder: {json.dumps(candidate_files)}
    """

    # 4. Stream events using run_async
    async for event in runner.run_async(
        user_id="student",
        session_id=session_id,
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part(text=prompt)]
        ),
    ):
        if event.is_final_response():
            # This is the final output from the Test Agent
            final_text = event.content.parts[0].text
            try:
                yield {"event": "result", "data": json.loads(final_text)}
            except json.JSONDecodeError:
                yield {"event": "result", "data": {"raw_output": final_text}}
        else:
            # Emit intermediate progress
            agent_name = getattr(event, "agent_name", "pipeline")
            yield {"event": "progress", "data": f"{agent_name.replace('_', ' ').title()} is processing..."}
