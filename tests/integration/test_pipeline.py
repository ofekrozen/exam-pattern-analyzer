# tests/integration/test_pipeline.py
import asyncio
from unittest.mock import patch, MagicMock
from main import run_analysis_stream, build_pipeline


def run_analysis_sync(drive_folder_url, lecturer_name, course_name="Calculus", syllabus="Derivatives"):
    """Helper to run the async generator in synchronous tests."""
    async def collect():
        results = []
        async for event in run_analysis_stream(drive_folder_url, lecturer_name, course_name, syllabus, "test_session"):
            results.append(event)
        return results
    return asyncio.run(collect())


@patch('main.find_pdfs_dfs')
@patch('main.Runner')
def test_run_analysis_success(mock_runner_cls, mock_find_pdfs_dfs):
    # Setup mocks
    mock_find_pdfs_dfs.return_value = [
        {"id": "file_1", "name": "Calculus_Exam1.pdf", "size": 500}
    ]

    # Mock the ADK Runner instance and its run_async() output
    mock_runner = MagicMock()
    mock_runner_cls.return_value = mock_runner

    mock_event = MagicMock()
    mock_event.is_final_response.return_value = True
    mock_event.agent_name = "test_agent"

    # Dummy final response from test_agent (including validation_details and final_report)
    mock_response_json = {
        "status": "success",
        "validation_details": {
            "schema_check": "passed",
            "consistency_check": "passed",
            "warnings": []
        },
        "final_report": {
            "topic_frequency": [{"topic": "Derivatives", "frequency": 4}],
            "question_type_distribution": {"multiple_choice": 5},
            "lecturer_style_summary": ["Uses proofs"],
            "study_recommendations": ["Solve past exams"]
        }
    }
    import json
    mock_event.content.parts[0].text = json.dumps(mock_response_json)

    # Mock async generator for runner.run_async()
    async def mock_run_async(*args, **kwargs):
        yield mock_event

    mock_runner.run_async.side_effect = mock_run_async

    # Run the orchestrator
    events = run_analysis_sync(
        drive_folder_url="https://drive.google.com/drive/folders/1SCeb1nRR4ivUyFy8yrviPCg1yihm961c",
        lecturer_name="Dr. Cohen"
    )

    # Verify mock interactions
    mock_find_pdfs_dfs.assert_called_once_with(
        "https://drive.google.com/drive/folders/1SCeb1nRR4ivUyFy8yrviPCg1yihm961c"
    )
    mock_runner.run_async.assert_called_once()

    # Assert result structure
    final_event = [e for e in events if e.get("event") == "result"]
    assert len(final_event) > 0
    result = final_event[-1]["data"]

    assert result["status"] == "success"
    assert "final_report" in result
    assert result["final_report"]["topic_frequency"][0]["topic"] == "Derivatives"


def test_run_analysis_invalid_input():
    # Run with malformed Drive URL to trigger validation error
    events = run_analysis_sync(
        drive_folder_url="https://invalid-url.com/folders/123",
        lecturer_name="Dr. Cohen"
    )

    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) > 0
    assert "Invalid input" in error_events[0]["data"]
