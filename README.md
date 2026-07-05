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

Given a public Google Drive folder link, a lecturer's name, a course name, and a syllabus, the system:

1. Scans the folder for PDF exam files
2. Identifies (from the document **content**, not the filename) which
   exams belong to the target lecturer — robust even when files are
   typed, scanned, or inconsistently named
3. Extracts a full per-question breakdown of each matched exam
4. Synthesizes patterns across all exams into a concrete study report
5. Validates the output format and structural integrity of the final study recommendations

## 🏗️ Architecture

The system uses a 5-step sequential agent pipeline orchestrated via the Google Agent Development Kit (ADK), alongside a FastAPI streaming backend.

```text
User Input (Drive link + lecturer name + course name + syllabus)
        │
        ▼
   [Validator]  ← Pydantic sanitization layer
        │
        ▼
[List PDF Files]  ← Plain Drive API call (no LLM needed)
        │
        ▼
[Security Agent] ──▶ LLM reasoning check for prompt injections/jailbreaks
        │ session state: security_status
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
        │ session state: raw_report
        ▼
[Test Agent]  ← pure reasoning, no tools
        │                       (validates format and guarantees schema compliance)
        ▼
   Final Study Report (JSON) streamed via Server-Sent Events (SSE)
```

A standalone **MCP server** (`mcp_server/server.py`) also exposes the
Drive-folder-scanning capability as a reusable tool, independent of this
specific pipeline.

## 🔑 Key Concepts Demonstrated

- ✅ **Multi-Agent System (ADK)** — `SequentialAgent` with 5 specialized
  sub-agents, chained via shared session state.
- ✅ **Real-Time Streaming** — A FastAPI backend pushes pipeline progress, tool calls, and status updates via SSE to a vanilla JS frontend.
- ✅ **MCP Server** — exposes Drive folder scanning as a standard tool.
- ✅ **Security Features** — Double-layered validation (Pydantic + Behavioral LLM Security Agent), prompt-injection guardrails, API-key-only access, and file scanning caps.
- ✅ **Agent Skills** — each agent has a narrow, well-defined responsibility.
- ✅ **Multimodal understanding** — Gemini reads both typed and scanned/handwritten PDFs natively, no separate OCR pipeline.

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
The folder must be shared as **"Anyone with the link can view"**.

### 7. Run the Web Interface
The recommended way to run the application is through the FastAPI web server, which provides a rich frontend UI.

```bash
uvicorn api.app:app --reload
```
Then navigate to `http://localhost:8000` in your browser.

*(You can still run the pipeline programmatically or interactively via `python main.py`)*

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

- All user input is validated and sanitized deterministically and behaviorally.
- A dedicated **Security Agent** enforces STRIDE alignment.
- The `skip_if_unsafe_callback` ensures no tools execute if threats are detected.
- Access is API-key-only and read-only — no OAuth, no write access, no access to private folders.

## 📁 Project Structure

```text
exam-pattern-analyzer/
├── main.py                       # Orchestrator and core pipeline logic
├── api/
│   └── app.py                    # FastAPI server & SSE streaming endpoints
├── frontend/
│   ├── index.html                # Web UI
│   ├── style.css
│   └── app.js
├── agents/
│   ├── identifier_agent.py       # Matches PDFs to target lecturer
│   ├── exam_analyzer_agent.py    # Extracts per-question structure
│   ├── pattern_synthesizer_agent.py # Synthesizes study report
│   └── test_agent.py             # QA and schema validation
├── security/
│   ├── security_agent.py         # Behavioral prompt injection analysis
│   └── validators.py             # Pydantic schema validation
├── tools/
│   ├── drive_client.py           # Public Drive API access
│   └── gemini_vision.py          # Multimodal PDF analysis
├── tests/                        # Comprehensive test suite (unit, integration, e2e)
└── mcp_server/
    └── server.py                 # MCP server: exposes Drive scanning
```

## 🛠️ Built With

Built using Google's official [Agent Development Kit (ADK)](https://google.github.io/adk-docs/), Gemini API, FastAPI for async streaming, and Vanilla JS for an interactive reactive frontend.
