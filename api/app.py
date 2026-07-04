from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import uuid
import asyncio

# Import the new async streaming function from main.py
from main import run_analysis_stream

app = FastAPI(title="Exam Pattern Analyzer API")

# Enable CORS for the frontend UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/analyze/stream")
async def stream_endpoint(
    drive_folder_url: str = Query(..., description="The public Google Drive folder URL"),
    lecturer_name: str = Query(..., description="The lecturer's name"),
    course_name: str = Query(..., description="The course's name"),
    syllabus: str = Query(..., description="The course's syllabus")
):
    # Generate a unique session ID per request to prevent state collisions
    session_id = str(uuid.uuid4())

    async def event_generator():
        try:
            async for update in run_analysis_stream(
                drive_folder_url=drive_folder_url,
                lecturer_name=lecturer_name,
                course_name=course_name,
                syllabus=syllabus,
                session_id=session_id
            ):
                # Standard Server-Sent Events (SSE) formatting
                yield f"event: {update['event']}\ndata: {json.dumps(update['data'])}\n\n"
                # Small sleep to ensure chunks flush cleanly to the client
                await asyncio.sleep(0.01)
        except Exception as e:
            yield f"event: error\ndata: {json.dumps(f'Server error: {str(e)}')}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Mount the frontend static files at the root so visiting http://localhost:8000 serves the UI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
