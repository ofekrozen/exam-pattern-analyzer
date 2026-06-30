# 🔍 Exam Pattern Analyzer

> A multi-agent system that scans a lecturer's past exams in Google Drive,
> deciphers each exam's structure, and produces actionable study
> recommendations based on recurring patterns.

## 🎯 The Problem

Students preparing for an exam often have access to a lecturer's past exams
but no time (or skill) to systematically analyze them: which topics recur,
how questions are typically phrased, what the point distribution looks
like. This insight is exactly what separates targeted, effective studying
from generic review.

## 💡 The Solution

Given a public Google Drive folder link and a lecturer's name, the system:

1. Scans the folder for PDF exam files
2. Identifies (from the document **content**, not the filename) which
   exams belong to the target lecturer — robust even when files are
   typed, scanned, or inconsistently named
3. Extracts a full per-question breakdown of each matched exam
4. Synthesizes patterns across all exams into a concrete study report

## 🏗️ Architecture

```
User Input (Drive link + lecturer name)
        │
        ▼
   [Validator]  ← Security layer: sanitizes input, caps file count
        │
        ▼
[List PDF Files]  ← Plain Drive API call (no LLM needed)
        │
        ▼
[Identifier Agent] ──uses──▶ check_lecturer_match tool
        │                     (downloads PDF, asks Gemini who the
        │                      lecturer is, fuzzy-matches the name)
        │ session state: matched_exams
        ▼
[Exam Analyzer Agent] ──uses──▶ analyze_exam tool
        │                        (sends full PDF to Gemini, extracts
        │                         per-question topic/type/points)
        │ session state: exam_analyses
        ▼
[Pattern Synthesizer Agent]  ← pure reasoning, no tools
        │                       (finds recurring topics, lecturer's
        │                        question style, study tips)
        ▼
   Final Study Report (JSON)
```

A standalone **MCP server** (`mcp_server/server.py`) also exposes the
Drive-folder-scanning capability as a reusable tool, independent of this
specific pipeline.

## 🔑 Key Concepts Demonstrated

- ✅ **Multi-Agent System (ADK)** — `SequentialAgent` with 3 specialized
  sub-agents, chained via shared session state (`output_key`)
- ✅ **MCP Server** — exposes Drive folder scanning as a standard tool
- ✅ **Security Features** — Pydantic input validation, prompt-injection
  guardrails on free-text fields, API-key-only access (no broad OAuth
  scopes), and a hard cap on files scanned per request
- ✅ **Agent Skills** — each agent has a narrow, well-defined
  responsibility with tools scoped specifically to that job
- ✅ **Multimodal understanding** — Gemini reads both typed and
  scanned/handwritten PDFs natively, no separate OCR pipeline

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/exam-pattern-analyzer
cd exam-pattern-analyzer
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Enable the required Google Cloud APIs
On the **same** Google Cloud project as your Gemini API key, enable:
- **Generative Language API** (for Gemini)
- **Google Drive API** (for listing/reading the public folder)

### 5. Configure your API key
```bash
cp .env.example .env
# Edit .env and add your Google AI Studio / Cloud API key
```

### 6. Share the target Drive folder publicly
The folder must be shared as **"Anyone with the link can view"**. This
keeps the security model simple (no OAuth, no stored user credentials) —
intentionally, the system never requests access to private files.

### 7. Run it
```python
from main import run_analysis

result = run_analysis(
    drive_folder_url="https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
    lecturer_name="Dr. Cohen",
)
print(result)
```

Or simply edit the example at the bottom of `main.py` and run:
```bash
python main.py
```

## 📤 Output Format

```json
{
  "topic_frequency": [...],
  "question_type_distribution": {...},
  "lecturer_style_summary": [...],
  "study_recommendations": [...]
}
```

## 🔒 Security Notes

- All user input (Drive URL, lecturer name) is validated and sanitized
  before reaching any agent or API call
- The lecturer-name field is checked against prompt-injection patterns
- Access is API-key-only and read-only — no OAuth, no write access, no
  access to private folders
- File scanning is capped (`MAX_FILES_TO_SCAN`) to bound cost and prevent
  abuse via oversized folders
- API keys are never hardcoded — loaded from environment variables only

## 📁 Project Structure

```
exam-pattern-analyzer/
├── main.py                       # Entry point and orchestrator
├── requirements.txt
├── .env.example
├── agents/
│   ├── identifier_agent.py       # Matches PDFs to the target lecturer
│   ├── exam_analyzer_agent.py    # Extracts per-question structure
│   └── pattern_synthesizer_agent.py  # Produces the final study report
├── tools/
│   ├── validators.py             # Input validation and security
│   ├── drive_client.py           # Public Drive API access (no OAuth)
│   └── gemini_vision.py          # Multimodal PDF analysis via Gemini
└── mcp_server/
    └── server.py                 # MCP server: exposes Drive scanning
```

## 🛠️ Built With

Built using Google's official [Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
and the Gemini API, following Google's recommended patterns for
multi-agent orchestration (`SequentialAgent` + shared session state) and
structured output (`response_mime_type="application/json"`).
