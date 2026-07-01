# agents/pattern_synthesizer_agent.py
# The Pattern Synthesizer Agent is a pure-reasoning agent (no tools).
# It looks across ALL analyzed exams and produces the final report:
# recurring topics, the lecturer's question style, and concrete,
# actionable study recommendations for the student.

from google.adk.agents import LlmAgent
from config import LLM_MODEL


def create_pattern_synthesizer_agent() -> LlmAgent:
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
            "past exams from the same lecturer and identify recurring "
            "patterns in topics, question types, and phrasing style, then "
            "translate that into actionable study recommendations."
        ),
        instruction="""
        You will receive 'exam_analyses' from session state — structured
        breakdowns of multiple past exams from the same lecturer.

        Produce a final report covering:

        1. "topic_frequency": which topics appear most often across exams,
           ranked by frequency (tells the student what to prioritize).
        2. "question_type_distribution": breakdown of multiple_choice vs.
           open_ended vs. calculation etc., across all analyzed exams.
        3. "lecturer_style_summary": 3-5 bullet observations about how
           this lecturer phrases questions (e.g. "prefers application word
           problems over pure theory", "always includes one proof
           question", "rarely repeats exact past questions but reuses
           topics").
        4. "study_recommendations": 5-8 concrete, actionable study tips
           directly derived from the patterns above (e.g. "Practice at
           least 3 calculation problems on [topic X] — it appeared in 4/5
           exams").

        Be specific — reference the actual topics and patterns you found
        in the data, not generic study advice. Output as clean JSON only,
        no explanation text outside it.
        """,
        output_key="final_report",
    )
