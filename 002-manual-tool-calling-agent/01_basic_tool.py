import requests


# Tool implementation.
# This is a normal Python function. The LLM does not execute it directly.
def add(input_1: float | int, input_2: float | int):
    """
    Adds 2 numbers and returns the result.
    """
    return input_1 + input_2


# Ollama local chat API endpoint.
ollama_url = "http://localhost:11434/api/chat"


# Tool schemas exposed to the LLM.
# The schema tells the model:
# - which tools are available
# - what each tool does
# - which arguments are required
#
# This does not execute the Python function.
tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Adds 2 numbers and returns the result",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_1": {
                        "type": "number",
                    },
                    "input_2": {
                        "type": "number",
                    },
                },
                "required": ["input_1", "input_2"],
            },
        },
    }
]


# Function registry.
# This maps the tool name returned by the model
# to the actual Python function that the controller is allowed to execute.
functions = {
    "add": add,
}


# Conversation history sent to the model.
messages = [
    {
        "role": "system",
        "content": "If tools are available to perform a task, use the appropriate tool.",
    },
    {
        "role": "user",
        "content": "My friend has 4 cars and I have 3 cars, how many total cars do we have?",
    },
]


# Request payload.
# Along with the conversation, we also send the available tool definitions.
payload = {
    "model": "qwen3:8b",
    "messages": messages,
    "tools": tools,
    "stream": False,
}


# Send request to the LLM.
res = requests.post(ollama_url, json=payload)
response = res.json()

# Print the full raw response while learning/debugging.
print(response)


# Read the tool calls proposed by the model.
#
# Important:
# At this point the model has only requested a tool call.
# No Python function has been executed yet.
tool_calls = response["message"]["tool_calls"]
print(tool_calls)


# For this basic example, use the first proposed tool call.
tool_call_function_name = tool_calls[0]["function"]["name"]
tool_call_function_arguments = tool_calls[0]["function"]["arguments"]

print(tool_call_function_name)
print(tool_call_function_arguments)


# Controller execution step.
#
# The controller takes the tool name proposed by the model,
# finds the corresponding allowed Python function in the registry,
# and executes it with the model-provided arguments.
func = functions[tool_call_function_name]

if func:
    result = func(**tool_call_function_arguments)
else:
    result = "Function not found."


# This is only the Python tool result.
#
# In this first example, we stop here.
# In the next agent-loop example, this result will be sent back
# to the LLM using a message with role="tool".
print(result)
