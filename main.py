# main.py
# Entry point for the Exam Pattern Analyzer.
#
# Pipeline:
#   1. Validate input (security)
#   2. List candidate PDF files in the public Drive folder (plain API call)
#   3. Identifier Agent  — filters files down to the target lecturer's exams
#   4. Exam Analyzer Agent — extracts per-question structure for each
#   5. Pattern Synthesizer Agent — produces the final study report

import os
import json
from dotenv import load_dotenv

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from tools.validators import AnalysisRequest
from tools.drive_client import list_pdf_files
from agents.identifier_agent import create_identifier_agent
from agents.exam_analyzer_agent import create_exam_analyzer_agent
from agents.pattern_synthesizer_agent import create_pattern_synthesizer_agent

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    raise EnvironmentError(
        "GOOGLE_API_KEY not found. Copy .env.example to .env and fill it in."
    )


def build_pipeline() -> SequentialAgent:
    """Builds the 3-agent sequential pipeline. Each agent reads/writes shared session state."""
    return SequentialAgent(
        name="exam_pattern_pipeline",
        description=(
            "Identifies a lecturer's past exams in a Drive folder, analyzes "
            "their structure, and synthesizes study recommendations."
        ),
        sub_agents=[
            create_identifier_agent(),
            create_exam_analyzer_agent(),
            create_pattern_synthesizer_agent(),
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

    # --- Steps 2-4: Run the agent pipeline ---
    prompt = f"""
    Target lecturer: {request.lecturer_name}

    Candidate exam files in the folder:
    {json.dumps(candidate_files, indent=2, ensure_ascii=False)}

    Find which files belong to this lecturer, analyze the structure of
    each matched exam, and produce a final study pattern report.
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
