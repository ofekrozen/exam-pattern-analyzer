import inspect
from google.adk.agents import LlmAgent

# Print the source of LlmAgent run or execute methods
print("--- LlmAgent ---")
for name, member in inspect.getmembers(LlmAgent):
    if name in ['run', '_execute', 'execute']:
        print(f"Method: {name}")
        print(inspect.getsource(member))
