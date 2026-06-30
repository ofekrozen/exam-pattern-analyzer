# mcp_server/server.py
# MCP server that exposes Google Drive folder scanning as a standard,
# reusable tool — demonstrating the MCP Server requirement in a way
# that's also genuinely useful: any MCP-compatible agent or client could
# reuse this exam-folder-scanning capability.

from mcp.server.fastmcp import FastMCP
from tools.drive_client import list_pdf_files

mcp = FastMCP("exam-drive-server")


@mcp.tool()
def list_exam_pdfs(drive_folder_url: str) -> list[dict]:
    """
    Lists PDF files in a public Google Drive folder.

    The folder must be shared as 'Anyone with the link can view'.
    Returns a capped list (see MAX_FILES_TO_SCAN) of {id, name, size}.

    Args:
        drive_folder_url: Full Google Drive folder URL.
    """
    return list_pdf_files(drive_folder_url)


if __name__ == "__main__":
    mcp.run(transport="stdio")
