# 🤖 Agent Development Guidelines (.agents.md)

Welcome, Agent! This file governs development standards, directory structures, testing pipelines, and security controls for the **Exam Pattern Analyzer** repository. You must read, respect, and enforce these patterns whenever you modify or extend this codebase.

---

## 🏗️ Multi-Agent Architecture

We use Google's **Agent Development Kit (ADK)** to orchestrate a 5-step sequential agent pipeline defined in [main.py](file:///c:/Users/ofeko/OneDrive/Desktop/Ofek/My_Projects/Google_5day_Agents/exam-pattern-analyzer/exam-pattern-analyzer/main.py).

### The Pipeline Sequence
1. **Security Agent** (`security/security_agent.py`): Checks the safety of input parameters (`lecturer_name` and `drive_folder_url`) for jailbreaks or prompt injections.
2. **Identifier Agent** (`agents/identifier_agent.py`): Downloads candidate PDFs and fuzzy-matches their content with the target lecturer.
3. **Exam Analyzer Agent** (`agents/exam_analyzer_agent.py`): Parses matched PDFs and extracts detailed question structures.
4. **Pattern Synthesizer Agent** (`agents/pattern_synthesizer_agent.py`): Generates a raw study report by finding recurring patterns.
5. **Test Agent** (`agents/test_agent.py`): Performs QA validation and fixes schema errors in the synthesizer output.

---

## 🔒 Security & Safe-Execution Rules

1. **Dedicated Security Folder:** All validation, sanitization, and safety-auditing agents or functions must reside in the [`security/`](file:///c:/Users/ofeko/OneDrive/Desktop/Ofek/My_Projects/Google_5day_Agents/exam-pattern-analyzer/exam-pattern-analyzer/security/) directory.
2. **Double-Layer Validation:**
   - **Deterministic:** Strict regex and Pydantic validation inside [`security/validators.py`](file:///c:/Users/ofeko/OneDrive/Desktop/Ofek/My_Projects/Google_5day_Agents/exam-pattern-analyzer/exam-pattern-analyzer/security/validators.py).
   - **Behavioral:** LLM reasoning in the `Security Agent`.
3. **Safety Callback Enforcements:**
   - All downstream agents (`Identifier`, `Exam Analyzer`, `Pattern Synthesizer`, and `Test` Agents) must register the `skip_if_unsafe_callback` callback as their `before_model_callback`.
   - If `security_status` in session state flags a request as unsafe (`is_safe = False`), the callback will intercept the agent execution and return the error JSON directly, preventing tool execution and LLM calls.
4. **STRIDE Alignment:** All changes must comply with the threat vectors and controls documented in the [STRIDE Threat Model](file:///c:/Users/ofeko/OneDrive/Desktop/Ofek/My_Projects/Google_5day_Agents/exam-pattern-analyzer/exam-pattern-analyzer/security/stride_threat_model.md).
5. **No Hardcoded Secrets:** Never hardcode credentials. Standardize secret loading through environment variables, checked statically via [`.semgrep.yaml`](file:///c:/Users/ofeko/OneDrive/Desktop/Ofek/My_Projects/Google_5day_Agents/exam-pattern-analyzer/exam-pattern-analyzer/.semgrep.yaml).

---

## 🧪 Testing & Directory Conventions

Any new features, tools, or helpers must be accompanied by comprehensive tests. Follow this exact folder structure:

```
tests/
├── unit/            # For testing isolated logic, name matching, and constructors
├── integration/     # For testing API wrappers and overall orchestrator coordination
└── e2e/             # For simulating complete sequential runs with mocked models
```

### Running Tests
All tests are run using `pytest`. Before committing your work, verify that the entire test suite passes:
```bash
.\venv\Scripts\pytest
```

---

## ⚙️ Development Workflow & Git Hooks

- **Pre-commit configuration:** We use `pre-commit` to lint YAML, clean whitespaces, and run `pytest` before commits. Install it via:
  ```bash
  .\venv\Scripts\pre-commit install
  ```
- **Static Analysis (Semgrep):** In supported Linux/WSL/CI environments, run:
  ```bash
  semgrep scan --config .semgrep.yaml
  ```
