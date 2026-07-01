import asyncio
import json
import sys
from main import run_analysis_stream

sys.stdout.reconfigure(encoding='utf-8')

async def test():
    url = "https://drive.google.com/drive/folders/18gYnT893_CqKE-rP8aD75fmT_Z64K2lo"
    lecturer = "כרמית חזאי"
    print(f"Testing with URL: {url}")
    print(f"Lecturer: {lecturer}")

    async for event in run_analysis_stream(url, lecturer, "test-session-123"):
        print(event)

if __name__ == "__main__":
    asyncio.run(test())
