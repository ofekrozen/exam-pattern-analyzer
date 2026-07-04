# tools/report_verifier.py
# Deterministic helper to verify the integrity and schema of the generated study report.

import json
from typing import Any

def verify_report_integrity(report_str: str) -> dict:
    """
    Validates the generated final study pattern report.
    Checks:
    - Valid JSON format
    - Presence of required fields: 'summary'
    - Presence of at least one of 'exams' or 'student_solutions' lists
    - Correct formatting of 'exams' and 'student_solutions' if present
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
    if "summary" not in parsed:
        errors.append("Missing required key: 'summary'")

    has_exams = "exams" in parsed and isinstance(parsed["exams"], list) and len(parsed["exams"]) > 0
    has_solutions = "student_solutions" in parsed and isinstance(parsed["student_solutions"], list) and len(parsed["student_solutions"]) > 0

    if not has_exams and not has_solutions:
        if "exams" not in parsed and "student_solutions" not in parsed:
            errors.append("Missing required key: must have either 'exams' or 'student_solutions'")
        else:
            errors.append("At least one of 'exams' or 'student_solutions' must be a non-empty list")

    if errors:
        return {
            "is_valid": False,
            "errors": errors,
            "parsed_report": parsed
        }

    # 3. Check data types and placeholder values
    summary = parsed.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("'summary' must be a non-empty string")

    exams = parsed.get("exams", [])
    if not isinstance(exams, list):
        errors.append("'exams' must be a list")
    else:
        for idx, exam in enumerate(exams):
            if not isinstance(exam, dict):
                errors.append(f"Exam at index {idx} must be a dictionary")
                continue
            if "exam_name" not in exam or not isinstance(exam["exam_name"], str):
                errors.append(f"Exam at index {idx} is missing a valid 'exam_name'")
            if "questions" not in exam or not isinstance(exam["questions"], list):
                errors.append(f"Exam at index {idx} is missing a valid 'questions' list")
                continue

            for q_idx, q in enumerate(exam["questions"]):
                if not isinstance(q, dict):
                    errors.append(f"Question at index {q_idx} in exam {idx} must be a dictionary")
                    continue
                if "q_number" not in q:
                    errors.append(f"Question at index {q_idx} in exam {idx} is missing 'q_number'")
                if "q_content" not in q or not isinstance(q["q_content"], str):
                    errors.append(f"Question at index {q_idx} in exam {idx} is missing 'q_content' string")
                if "tags" not in q or not isinstance(q["tags"], list):
                    errors.append(f"Question at index {q_idx} in exam {idx} is missing 'tags' list")

    solutions = parsed.get("student_solutions", [])
    if not isinstance(solutions, list):
        errors.append("'student_solutions' must be a list")
    else:
        for idx, sol in enumerate(solutions):
            if not isinstance(sol, dict):
                errors.append(f"Solution at index {idx} must be a dictionary")
                continue
            if "file_name" not in sol or not isinstance(sol["file_name"], str):
                errors.append(f"Solution at index {idx} is missing a valid 'file_name'")
            if "score_deductions" not in sol or not isinstance(sol["score_deductions"], list):
                errors.append(f"Solution at index {idx} is missing a valid 'score_deductions' list")
                continue

            for d_idx, d in enumerate(sol["score_deductions"]):
                if not isinstance(d, dict):
                    errors.append(f"Deduction at index {d_idx} in solution {idx} must be a dictionary")
                    continue
                if "q_number" not in d:
                    errors.append(f"Deduction at index {d_idx} in solution {idx} is missing 'q_number'")
                if "mistake" not in d or not isinstance(d["mistake"], str):
                    errors.append(f"Deduction at index {d_idx} in solution {idx} is missing 'mistake' string")
                if "deduction_reason" not in d or not isinstance(d["deduction_reason"], str):
                    errors.append(f"Deduction at index {d_idx} in solution {idx} is missing 'deduction_reason' string")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "parsed_report": parsed
    }
