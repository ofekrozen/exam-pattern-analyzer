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
from dotenv import load_dotenv

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from google.adk.models.llm_response import LlmResponse

from security.validators import AnalysisRequest
from tools.drive_client import list_pdf_files
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


def skip_if_unsafe_callback(ctx, request) -> LlmResponse | None:
    """
    Bypasses LLM model calls for downstream agents if the Security Agent
    has flagged the request as unsafe.
    """
    security_status = ctx.state.get("security_status")
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


def build_pipeline() -> SequentialAgent:
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

    return SequentialAgent(
        name="exam_pattern_pipeline",
        description=(
            "Identifies a lecturer's past exams in a Drive folder, analyzes "
            "their structure, and synthesizes study recommendations, while enforcing "
            "security and quality controls."
        ),
        sub_agents=[
            security_agent,
            identifier_agent,
            exam_analyzer_agent,
            pattern_synthesizer_agent,
            test_agent,
        ],
    )


def run_analysis(drive_folder_url: str, lecturer_name: str) -> dict:
    """
    Main entry point: validates input, scans the Drive folder, and runs
    the full agent pipeline to produce a study report.
    """

    # --- Security: validate all input before any API call ---
    try:
        request = AnalysisRequest(
            drive_folder_url=drive_folder_url, lecturer_name=lecturer_name
        )
    except ValueError as e:
        return {"error": f"Invalid input: {str(e)}"}

    # --- Step 1: List candidate PDF files (no LLM needed for this step) ---
    try:
        candidate_files = list_pdf_files(request.drive_folder_url)
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to list Drive files: {str(e)}"}

    if not candidate_files:
        return {"error": "No PDF files found in this folder."}

    # --- Steps 2-5: Run the agent pipeline ---
    prompt = f"""
    Target lecturer: {request.lecturer_name}

    Candidate exam files in the folder:
    {json.dumps(candidate_files, indent=2, ensure_ascii=False)}

    Check input safety, find which files belong to this lecturer, analyze the structure of
    each matched exam, and produce a final verified study pattern report.
    """

    session_service = InMemorySessionService()
    session_service.create_session(
        app_name="exam_analyzer", user_id="student", session_id="s1"
    )

    pipeline = build_pipeline()
    runner = Runner(
        agent=pipeline, app_name="exam_analyzer", session_service=session_service
    )

    print(
        f"\n🔎 Scanning {len(candidate_files)} PDF(s) for exams by "
        f"'{request.lecturer_name}'...\n"
    )

    events = runner.run(
        user_id="student",
        session_id="s1",
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part(text=prompt)]
        ),
    )

    for event in events:
        if event.is_final_response():
            final_text = event.content.parts[0].text
            try:
                return json.loads(final_text)
            except json.JSONDecodeError:
                return {"raw_output": final_text}

    return {"error": "No response from pipeline"}


if __name__ == "__main__":
    result = run_analysis(
        drive_folder_url="https://drive.google.com/drive/folders/1SCeb1nRR4ivUyFy8yrviPCg1yihm961c",
        lecturer_name="REPLACE_WITH_LECTURER_NAME",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
