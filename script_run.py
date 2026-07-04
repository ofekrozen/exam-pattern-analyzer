import sys
sys.stdout.reconfigure(encoding='utf-8')
import asyncio
import uuid
import json
from google.genai import types as genai_types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from main import build_pipeline
from tools.drive_client import find_pdfs_dfs
from dotenv import load_dotenv

async def test_backend():
    load_dotenv()
    url = "https://drive.google.com/drive/folders/18gYnT893_CqKE-rP8aD75fmT_Z64K2lo"
    lecturer = "כרמית חזאי"
    course = "אוטומטים וחישוביות"
    syllabus = "סילבוס..."

    session_id = str(uuid.uuid4())

    candidate_files = find_pdfs_dfs(url)

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="exam_analyzer", user_id="student", session_id=session_id
    )

    pipeline = build_pipeline(candidate_files, lecturer, course, syllabus)
    runner = Runner(agent=pipeline, app_name="exam_analyzer", session_service=session_service)

    prompt = f"Target lecturer: {lecturer}\nCourse name: {course}\nSyllabus: {syllabus}"

    print("Running runner.run_async...")
    async for event in runner.run_async(
        user_id="student",
        session_id=session_id,
        new_message=genai_types.Content(
            role="user", parts=[genai_types.Part(text=prompt)]
        ),
    ):
        print(f"Event is_final_response: {event.is_final_response()}")
        try:
            print(f"Function calls: {event.get_function_calls()}")
        except Exception as e:
            print(f"Could not get function calls: {e}")
        try:
            print(f"Text output: {event.content.parts[0].text}")
        except Exception as e:
            print(f"No text output.")

if __name__ == "__main__":
    asyncio.run(test_backend())
