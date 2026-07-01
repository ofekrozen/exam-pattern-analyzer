import inspect
from google.adk.workflow._base_node import BaseNode

source = inspect.getsource(BaseNode._validate_output_data)
print(source)
