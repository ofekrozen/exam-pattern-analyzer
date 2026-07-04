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
    # 1. security_agent response
    # 2. identifier_agent response
    # 3. exam_analyzer_agent response
    # 4. pattern_synthesizer_agent response
    # 5. test_agent response

    # Mock responses list
    from google.adk.models.llm_response import LlmResponse
    import json

    responses = [
        # Security Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"is_safe": true, "reason": null}')])),
        # Identifier Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"matched_exams": [{"file_id": "f1", "file_name": "Exam.pdf", "course_name": "Course"}]}')])),
        # Exam Analyzer Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"exams": [{"file_name": "Exam.pdf", "document_type": "exam", "total_questions": 1, "questions": []}], "student_solutions": []}')])),
        # Pattern Synthesizer Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"summary": "Test summary", "exams": [], "student_solutions": []}')])),
        # Test Agent
        LlmResponse(content=genai_types.Content(role='model', parts=[genai_types.Part(text='{"status": "success", "validation_details": {"schema_check": "passed", "consistency_check": "passed", "warnings": []}, "final_report": {"summary": "Test summary", "exams": [], "student_solutions": []}}')]))
    ]

    # Define an async side effect for running the flow
    async def mock_run_async(ctx):
        if responses:
            resp = responses.pop(0)
            import json
            class MockEventDict(dict):
                def __getattr__(self, name):
                    return MagicMock()

            data = json.loads(resp.content.parts[0].text)
            out = MockEventDict(data)
            # Make sure get_function_calls is callable and returns empty to avoid issues
            out.get_function_calls = lambda: []
            yield out

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
    last_response = final_responses[-1]
    if getattr(last_response, "output", None) is not None:
        parsed = last_response.output
    else:
        last_text = last_response.content.parts[0].text
        parsed = json.loads(last_text)
    assert parsed["status"] == "success"
