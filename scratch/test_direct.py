import asyncio
from main import run_analysis_stream
import traceback

async def run():
    try:
        async for update in run_analysis_stream(
            drive_folder_url="https://drive.google.com/drive/folders/18gYnT893_CqKE-rP8aD75fmT_Z64K2lo",
            lecturer_name="כרמית חזאי",
            course_name="אוטומטים וחישוביות",
            syllabus="1. אוטומטים ושפות רגולריות - אוטומט סופי ד",
            session_id="test_session"
        ):
            print("UPDATE:", update)
    except Exception as e:
        print("EXCEPTION CAUGHT!")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
