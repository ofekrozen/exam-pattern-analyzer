# security/validators.py
# Security layer: validates all user input before any agent or API call runs.
# This guards against malformed URLs, prompt injection via the lecturer name
# field, and unbounded API usage (cost/quota protection).

import re
import difflib
from pydantic import BaseModel, field_validator

DRIVE_FOLDER_PATTERN = re.compile(r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)")

# Safety cap: limits how many files we scan per request.
# Protects API quota/cost and prevents abuse via huge folders.
MAX_FILES_TO_SCAN = 15


class AnalysisRequest(BaseModel):
    """Validated input for an exam pattern analysis request."""
    drive_folder_url: str
    lecturer_name: str
    course_name: str
    syllabus: str

    @field_validator("drive_folder_url")
    @classmethod
    def must_be_valid_drive_folder(cls, v: str) -> str:
        v = v.strip()
        if not DRIVE_FOLDER_PATTERN.search(v):
            raise ValueError(
                "Must be a valid Google Drive folder link "
                "(format: drive.google.com/drive/folders/...)"
            )
        return v

    @field_validator("lecturer_name")
    @classmethod
    def sanitize_lecturer_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Lecturer name cannot be empty")
        if len(v) > 80:
            raise ValueError("Lecturer name too long (max 80 characters)")
        # Guardrail against prompt injection through this field
        forbidden = ["<", ">", "{", "}", "ignore previous", "system:", "\\"]
        for token in forbidden:
            if token.lower() in v.lower():
                raise ValueError(f"Invalid content in lecturer name: '{token}'")
        return v

    @field_validator("course_name")
    @classmethod
    def sanitize_course_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Course name cannot be empty")
        if len(v) > 100:
            raise ValueError("Course name too long (max 100 characters)")
        return v

    @field_validator("syllabus")
    @classmethod
    def sanitize_syllabus(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Syllabus cannot be empty")
        if len(v) > 120:
            raise ValueError("Syllabus too long (max 120 characters)")
        return v


def extract_folder_id(drive_folder_url: str) -> str:
    """Extracts the Drive folder ID from a full folder URL."""
    match = DRIVE_FOLDER_PATTERN.search(drive_folder_url)
    if not match:
        raise ValueError("Could not extract folder ID from URL")
    return match.group(1)


def normalize_name_for_matching(name: str) -> str:
    """
    Strips common academic titles so name comparison is robust.
    e.g. 'ד"ר כהן' and 'כהן' should be recognized as the same person.
    """
    titles = [
        'ד"ר', "דר'", "פרופ'", "פרופסור", "מר", "גב'",
        "dr.", "prof.", "professor", "mr.", "ms.", "mrs.",
    ]
    cleaned = name.strip().lower()
    for t in titles:
        cleaned = cleaned.replace(t, "")
    return cleaned.strip()


def names_match(target_name: str, extracted_name: str) -> bool:
    """Fuzzy match between the user-provided name and the name found in a PDF."""
    if not extracted_name:
        return False
    t_norm = normalize_name_for_matching(target_name)
    e_norm = normalize_name_for_matching(extracted_name)

    if not t_norm or not e_norm:
        return False

    t = t_norm.split()
    e = e_norm.split()

    # Fast path: Check exact token subset
    if all(part in e for part in t) or all(part in t for part in e):
        return True

    # Check string similarity using difflib
    # Ratio > 0.75 is a good threshold for minor typos
    if difflib.SequenceMatcher(None, t_norm, e_norm).ratio() > 0.75:
        return True

    # Check token-by-token similarity for partial matches with typos
    # (e.g. "כרמית חזאי" vs "ד"ר ברמית חזאי")
    matched_tokens = 0
    for t_token in t:
        for e_token in e:
            if difflib.SequenceMatcher(None, t_token, e_token).ratio() > 0.8:
                matched_tokens += 1
                break

    if len(t) > 0 and (matched_tokens / len(t)) >= 0.5:
        return True

    return False
