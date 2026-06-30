# tests/integration/test_pipeline.py
from unittest.mock import patch, MagicMock
from main import run_analysis, build_pipeline


@patch('main.list_pdf_files')
@patch('main.Runner')
def test_run_analysis_success(mock_runner_cls, mock_list_pdf_files):
    # Setup mocks
    mock_list_pdf_files.return_value = [
        {"id": "file_1", "name": "Calculus_Exam1.pdf", "size": 500}
    ]

    # Mock the ADK Runner instance and its run() output
    mock_runner = MagicMock()
    mock_runner_cls.return_value = mock_runner

    mock_event = MagicMock()
    mock_event.is_final_response.return_value = True

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
    mock_runner.run.return_value = [mock_event]

    # Run the orchestrator
    result = run_analysis(
        drive_folder_url="https://drive.google.com/drive/folders/1SCeb1nRR4ivUyFy8yrviPCg1yihm961c",
        lecturer_name="Dr. Cohen"
    )

    # Verify mock interactions
    mock_list_pdf_files.assert_called_once_with(
        "https://drive.google.com/drive/folders/1SCeb1nRR4ivUyFy8yrviPCg1yihm961c"
    )
    mock_runner.run.assert_called_once()

    # Assert result structure
    assert result["status"] == "success"
    assert "final_report" in result
    assert result["final_report"]["topic_frequency"][0]["topic"] == "Derivatives"


def test_run_analysis_invalid_input():
    # Run with malformed Drive URL to trigger validation error
    result = run_analysis(
        drive_folder_url="https://invalid-url.com/folders/123",
        lecturer_name="Dr. Cohen"
    )

    assert "error" in result
    assert "Invalid input" in result["error"]
