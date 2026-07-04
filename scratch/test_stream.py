import requests
import urllib.parse
import sys

def main():
    url = "http://localhost:8000/api/analyze/stream"
    params = {
        "drive_folder_url": "https://drive.google.com/drive/folders/18gYnT893_CqKE-rP8aD75fmT_Z64K2lo",
        "lecturer_name": "כרמית חזאי",
        "course_name": "אוטומטים וחישוביות",
        "syllabus": "1. אוטומטים ושפות רגולריות - אוטומט סופי ד"
    }
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"

    print(f"Connecting to {full_url}")
    with requests.get(full_url, stream=True) as r:
        if r.status_code != 200:
            print(f"Failed: {r.status_code}")
            print(r.text)
            return

        for line in r.iter_lines():
            if line:
                print(line.decode('utf-8'))
            else:
                print("--- EMPTY LINE (EVENT BOUNDARY) ---")

if __name__ == "__main__":
    main()
