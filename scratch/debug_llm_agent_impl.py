import inspect
from google.adk.agents.llm_agent import LlmAgent

# Print the source of LlmAgent._run_impl
print(inspect.getsource(LlmAgent._run_impl))
