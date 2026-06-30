# tests/unit/test_agents.py
from google.adk.agents import LlmAgent
from security.security_agent import create_security_agent
from agents.identifier_agent import create_identifier_agent
from agents.exam_analyzer_agent import create_exam_analyzer_agent
from agents.pattern_synthesizer_agent import create_pattern_synthesizer_agent
from agents.test_agent import create_test_agent

def test_security_agent_creation():
    agent = create_security_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "security_agent"
    assert agent.output_key == "security_status"
    assert agent.output_schema is not None


def test_identifier_agent_creation():
    agent = create_identifier_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "identifier_agent"
    assert agent.output_key == "matched_exams"
    assert len(agent.tools) == 1


def test_exam_analyzer_agent_creation():
    agent = create_exam_analyzer_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "exam_analyzer_agent"
    assert agent.output_key == "exam_analyses"
    assert len(agent.tools) == 1


def test_pattern_synthesizer_agent_creation():
    agent = create_pattern_synthesizer_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "pattern_synthesizer_agent"
    assert agent.output_key == "final_report"
    assert len(agent.tools) == 0


def test_test_agent_creation():
    agent = create_test_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "test_agent"
    assert agent.output_key == "validated_report"
    assert len(agent.tools) == 1
    assert agent.output_schema is not None
