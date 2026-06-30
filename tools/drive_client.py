# tools/drive_client.py
# Lightweight Google Drive client using an API key only (no OAuth).
# This ONLY works for folders/files shared as "Anyone with the link" —
# which is intentional: it keeps the security model simple and avoids
# requesting broad OAuth scopes for a hackathon-scale project.

import os
import requests
from security.validators import extract_folder_id, MAX_FILES_TO_SCAN

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_DRIVE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_DRIVE_API_KEY (or GOOGLE_API_KEY) not set")
    return api_key


def list_pdf_files(drive_folder_url: str) -> list[dict]:
    """
    Lists PDF files inside a PUBLIC Google Drive folder.

    Requires the folder to be shared as 'Anyone with the link can view'.

    Returns at most MAX_FILES_TO_SCAN files — a safety cap that protects
    API quota/cost and keeps response times reasonable for a demo.
    """
    api_key = _get_api_key()
    folder_id = extract_folder_id(drive_folder_url)
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"

    resp = requests.get(
        f"{DRIVE_API_BASE}/files",
        params={
            "q": query,
            "key": api_key,
            "fields": "files(id,name,size)",
            "pageSize": MAX_FILES_TO_SCAN,
        },
        timeout=20,
    )

    if resp.status_code == 403:
        raise PermissionError(
            "Access denied. Make sure the Drive folder is shared as "
            "'Anyone with the link' (public) — private/restricted folders "
            "are not supported by this API-key-only approach."
        )
    resp.raise_for_status()

    files = resp.json().get("files", [])
    return files[:MAX_FILES_TO_SCAN]


def download_file_bytes(file_id: str) -> bytes:
    """Downloads the raw bytes of a public Drive file by its ID."""
    api_key = _get_api_key()

    resp = requests.get(
        f"{DRIVE_API_BASE}/files/{file_id}",
        params={"alt": "media", "key": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content
