# tests/e2e/test_pipeline_e2e.py
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from main import build_pipeline


@patch('google.adk.agents.llm_agent.LLMRegistry.new_llm')
@patch('google.adk.agents.llm_agent.LlmAgent._llm_flow', new_callable=PropertyMock)
def test_pipeline_sequential_execution(mock_llm_flow_prop, mock_new_llm):
    # Setup mock LLM model
    mock_model = MagicMock()
    mock_new_llm.return_value = mock_model

    # We mock model responses for the pipeline agents:
    # 1. security_agent response: {"is_safe": true}
    # 2. identifier_agent response: {"matched_exams": [{"file_id": "f1", "file_name": "Exam.pdf"}]}
    # 3. exam_analyzer_agent response: {"exams": [{"file_name": "Exam.pdf", "total_questions": 1, "questions": []}]}
    # 4. pattern_synthesizer_agent response: {"topic_frequency": [], "question_type_distribution": {}, "lecturer_style_summary": [], "study_recommendations": []}
    # 5. test_agent response: {"status": "success", "validation_details": {"schema_check": "passed", "consistency_check": "passed", "warnings": []}, "final_report": {}}

    # Mock responses list
    from google.adk.models.llm_response import LlmResponse
    import json

    responses = [
        # Security Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"is_safe": true, "reason": null}')])),
        # Identifier Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"matched_exams": [{"file_id": "f1", "file_name": "Exam.pdf", "course_name": "Calculus"}]}')])),
        # Exam Analyzer Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"exams": [{"file_name": "Exam.pdf", "total_questions": 1, "questions": []}]}')])),
        # Pattern Synthesizer Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"topic_frequency": [], "question_type_distribution": {}, "lecturer_style_summary": [], "study_recommendations": []}')])),
        # Test Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"status": "success", "validation_details": {"schema_check": "passed", "consistency_check": "passed", "warnings": []}, "final_report": {}}')]))
    ]

    # Define an async side effect for running the flow
    async def mock_run_async(ctx):
        # Pop the first response
        if responses:
            resp = responses.pop(0)
            yield MagicMock(is_final_response=lambda: True, content=resp.content)

    # Mock the LLM flow property run_async
    mock_flow = MagicMock()
    mock_flow.run_async.side_effect = mock_run_async
    mock_llm_flow_prop.return_value = mock_flow

    pipeline = build_pipeline()

    # Setup runner and session
    session_service = InMemorySessionService()
    # Await session creation using asyncio run to avoid warnings
    asyncio.run(session_service.create_session(app_name="exam_analyzer", user_id="student", session_id="s1"))

    runner = Runner(agent=pipeline, app_name="exam_analyzer", session_service=session_service)

    # Run the pipeline
    events = runner.run(
        user_id="student",
        session_id="s1",
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part(text="Run analysis")]
        ),
    )

    # Collect final responses
    final_responses = [e for e in events if e.is_final_response()]
    assert len(final_responses) > 0

    # The last response from test_agent
    last_text = final_responses[-1].content.parts[0].text
    parsed = json.loads(last_text)
    assert parsed["status"] == "success"
