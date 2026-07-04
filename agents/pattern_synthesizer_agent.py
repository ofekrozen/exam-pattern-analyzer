# agents/pattern_synthesizer_agent.py
# The Pattern Synthesizer Agent is a pure-reasoning agent (no tools).
# It looks across ALL analyzed exams and produces the final report:
# recurring topics, the lecturer's question style, and concrete,
# actionable study recommendations for the student.

from google.adk.agents import LlmAgent
from config import LLM_MODEL


def create_pattern_synthesizer_agent() -> LlmAgent:
    from agents.schemas import FinalReport
    """
    Creates the Pattern Synthesizer Agent.

    Reads 'exam_analyses' from session state (structured breakdowns of
    multiple past exams from the same lecturer) and synthesizes patterns
    into a final, actionable study report.
    """
    return LlmAgent(
        name="pattern_synthesizer_agent",
        model=LLM_MODEL,
        description=(
            "You are an expert exam-pattern analyst. You study multiple "
            "past exams and student solutions from the same lecturer and identify recurring "
            "patterns in topics, question types, phrasing style, and common mistakes, then "
            "translate that into actionable study recommendations."
        ),
        instruction="""
        You will receive 'exam_analyses' from session state — structured
        breakdowns of multiple past exams and student solutions from the same lecturer.

        Produce a final report covering:

        1. A comprehensive "summary" string. This should be a detailed report on what the
           professor likes to ask in their exams and in what form, AND what mistakes students commonly make based on the score deductions. You MUST cite the specific source (file name/tab and question number) for insights derived from score deductions.
        2. "exams": A list of the exams analyzed, preserving the per-question breakdown.
        3. "student_solutions": A list of the solutions analyzed and their score deductions.

        Output ONLY a valid JSON matching the requested schema, with no explanation text outside it.
        """,
        output_schema=FinalReport,
        output_key="final_report",
    )
