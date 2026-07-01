import asyncio
import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

from tools.drive_client import find_pdfs_dfs
from agents.identifier_agent import check_lecturer_match

url = "https://drive.google.com/drive/folders/18gYnT893_CqKE-rP8aD75fmT_Z64K2lo"
lecturer = "כרמית חזאי"

files = find_pdfs_dfs(url)
print(f"Found {len(files)} files")

for f in files:
    print(f"Checking {f['name']} (ID: {f['id']})...")
    res = check_lecturer_match(f['id'], f['name'], lecturer)
    print(json.dumps(res, indent=2, ensure_ascii=False))
