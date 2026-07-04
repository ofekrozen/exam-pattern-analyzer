# tools/drive_client.py
# Lightweight Google Drive client using an API key only (no OAuth).
# This ONLY works for folders/files shared as "Anyone with the link" —
# which is intentional: it keeps the security model simple and avoids
# requesting broad OAuth scopes for a hackathon-scale project.

import re
import os
import requests
from security.validators import extract_folder_id, MAX_FILES_TO_SCAN

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_DRIVE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_DRIVE_API_KEY (or GOOGLE_API_KEY) not set")
    return api_key


def _recency_score(name: str, modified_time: str) -> tuple:
    """Returns (year, modifiedTime) for descending sort — higher = more recent."""
    years = _YEAR_RE.findall(name)
    year = max(int(y) for y in years) if years else 0
    return (year, modified_time)


def _list_pdfs_in_folder(folder_id: str, api_key: str) -> list[dict]:
    """Lists PDF files that are direct children of `folder_id`."""
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    resp = requests.get(
        f"{DRIVE_API_BASE}/files",
        params={
            "q": query,
            "key": api_key,
            "fields": "files(id,name,size,parents)",
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
    for f in files:
        parents = f.get("parents", [])
        f["parent_id"] = parents[0] if parents else folder_id
    return files


def _list_subfolders(folder_id: str, api_key: str) -> list[dict]:
    """Lists direct sub-folders of `folder_id`, including modifiedTime for ranking."""
    query = (
        f"'{folder_id}' in parents "
        "and mimeType='application/vnd.google-apps.folder' "
        "and trashed=false"
    )
    resp = requests.get(
        f"{DRIVE_API_BASE}/files",
        params={
            "q": query,
            "key": api_key,
            "fields": "files(id,name,modifiedTime)",
            "pageSize": 50,
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
    return resp.json().get("files", [])


def list_pdf_files(drive_folder_url: str) -> list[dict]:
    """
    Lists PDF files inside a PUBLIC Google Drive folder (root level only).

    Kept for backward compatibility with mcp_server/server.py.
    For new code, prefer find_pdfs_dfs() which also searches sub-folders.
    """
    api_key = _get_api_key()
    folder_id = extract_folder_id(drive_folder_url)
    files = _list_pdfs_in_folder(folder_id, api_key)
    return files[:MAX_FILES_TO_SCAN]


def find_pdfs_dfs(drive_folder_url: str, max_depth: int = 3) -> list[dict]:
    """
    Finds PDFs starting from the root folder. If the root is empty, performs
    a DFS into sub-folders ordered by most-recent year in the folder name
    (Drive modifiedTime as tiebreaker). Stops as soon as MAX_FILES_TO_SCAN
    total PDFs are collected or all sub-folders (up to max_depth) are visited.
    """
    api_key = _get_api_key()
    root_id = extract_folder_id(drive_folder_url)

    root_pdfs = _list_pdfs_in_folder(root_id, api_key)
    if root_pdfs:
        return root_pdfs[:MAX_FILES_TO_SCAN]

    visited: set[str] = {root_id}
    subfolders = _list_subfolders(root_id, api_key)
    subfolders.sort(
        key=lambda f: _recency_score(f["name"], f.get("modifiedTime", "")),
        reverse=True,
    )
    # Push in reverse order so the most-recent folder is popped (visited) first
    stack = [(f["id"], 1) for f in reversed(subfolders)]
    collected: list[dict] = []

    while stack and len(collected) < MAX_FILES_TO_SCAN:
        folder_id, depth = stack.pop()
        if folder_id in visited:
            continue
        visited.add(folder_id)

        pdfs = _list_pdfs_in_folder(folder_id, api_key)
        collected.extend(pdfs)

        if depth < max_depth:
            children = _list_subfolders(folder_id, api_key)
            children.sort(
                key=lambda f: _recency_score(f["name"], f.get("modifiedTime", "")),
                reverse=True,
            )
            for child in reversed(children):
                if child["id"] not in visited:
                    stack.append((child["id"], depth + 1))

    return collected[:MAX_FILES_TO_SCAN]


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
