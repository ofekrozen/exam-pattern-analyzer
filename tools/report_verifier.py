# tools/report_verifier.py
# Deterministic helper to verify the integrity and schema of the generated study report.

import json
from typing import Any

def verify_report_integrity(report_str: str) -> dict:
    """
    Validates the generated final study pattern report.
    Checks:
    - Valid JSON format
    - Presence of required fields: topic_frequency, question_type_distribution,
      lecturer_style_summary, study_recommendations
    - Data types are correct (lists vs dicts)
    - No empty/placeholder values

    Returns:
        A dictionary with keys: 'is_valid' (bool), 'errors' (list of strings),
        and 'parsed_report' (the parsed dict if valid, or None).
    """
    errors = []
    parsed = None

    # 1. Parse JSON
    try:
        # Clean any markdown block formatting if present
        cleaned_str = report_str.strip()
        if cleaned_str.startswith("```json"):
            cleaned_str = cleaned_str[7:]
        if cleaned_str.endswith("```"):
            cleaned_str = cleaned_str[:-3]
        cleaned_str = cleaned_str.strip()

        parsed = json.loads(cleaned_str)
    except json.JSONDecodeError as e:
        return {
            "is_valid": False,
            "errors": [f"Invalid JSON format: {str(e)}"],
            "parsed_report": None
        }

    if not isinstance(parsed, dict):
        return {
            "is_valid": False,
            "errors": ["Report must be a JSON object (dictionary) at the root level"],
            "parsed_report": None
        }

    # 2. Check required keys
    required_keys = [
        "topic_frequency",
        "question_type_distribution",
        "lecturer_style_summary",
        "study_recommendations"
    ]
    for key in required_keys:
        if key not in parsed:
            errors.append(f"Missing required key: '{key}'")

    if errors:
        return {
            "is_valid": False,
            "errors": errors,
            "parsed_report": parsed
        }

    # 3. Check data types and placeholder values
    # topic_frequency
    topic_freq = parsed.get("topic_frequency")
    if not isinstance(topic_freq, list):
        errors.append("'topic_frequency' must be a list of topics/frequencies")
    elif len(topic_freq) == 0:
        errors.append("'topic_frequency' list is empty")

    # question_type_distribution
    q_dist = parsed.get("question_type_distribution")
    if not isinstance(q_dist, dict):
        errors.append("'question_type_distribution' must be a dictionary")
    elif len(q_dist) == 0:
        errors.append("'question_type_distribution' dictionary is empty")

    # lecturer_style_summary
    style = parsed.get("lecturer_style_summary")
    if not isinstance(style, list):
        errors.append("'lecturer_style_summary' must be a list of observations")
    elif len(style) == 0:
        errors.append("'lecturer_style_summary' list is empty")
    else:
        for idx, item in enumerate(style):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"Observation at index {idx} in 'lecturer_style_summary' must be a non-empty string")

    # study_recommendations
    recs = parsed.get("study_recommendations")
    if not isinstance(recs, list):
        errors.append("'study_recommendations' must be a list of tips")
    elif len(recs) == 0:
        errors.append("'study_recommendations' list is empty")
    else:
        for idx, item in enumerate(recs):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"Recommendation at index {idx} in 'study_recommendations' must be a non-empty string")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "parsed_report": parsed
    }
