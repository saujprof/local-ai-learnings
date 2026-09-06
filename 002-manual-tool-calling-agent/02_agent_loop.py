import requests

# Tool implementations.
# These are normal Python functions.
# The LLM can request them, but cannot execute them directly.
def add(input_1: float | int, input_2: float | int):
    """
    Adds 2 numbers and returns the result.
    """
    return input_1 + input_2


def divide(input_1: float | int, input_2: float | int):
    """
    Divides 2 numbers and returns the result.
    """
    if input_2 == 0:
        return 0
    return input_1 / input_2


# Ollama local chat API endpoint.
ollama_url = "http://localhost:11434/api/chat"


# Tool schemas exposed to the LLM.
# These only describe which tools are available and
# what arguments each tool accepts.
tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Adds 2 numbers and returns the result",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_1": {"type": "number"},
                    "input_2": {"type": "number"},
                },
                "required": ["input_1", "input_2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "divide",
            "description": "Divides 2 numbers and returns the result",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_1": {"type": "number"},
                    "input_2": {"type": "number"},
                },
                "required": ["input_1", "input_2"],
            },
        },
    },
]


# Function registry.
# Maps tool names returned by the model to real Python functions
# that the controller is allowed to execute.
function_registry = {
    "add": add,
    "divide": divide,
}


# Conversation history.
messages = [
    {
        "role": "system",
        "content": "If tools are available to perform a task, use the appropriate tool.",
    },
    {
        "role": "user",
        "content": "I have 3 apples, my friend has 6 apples, and another friend has 3 apples. We need to collect all apples and distribute these among 4 children. How many apples each children get ?",
    },
]


# Payload keeps a reference to the same `messages` list.
# As messages are appended below, the next request receives
# the updated conversation history.
payload = {
    "model": "qwen3:8b",
    "messages": messages,
    "tools": tools,
    "stream": False,
}


# Manual agent/controller loop.
#
# Flow:
# LLM -> tool call -> controller executes -> tool result
# -> send updated history back to LLM -> repeat.
while True:
    print(messages)

    # Ask the model what to do next.
    res = requests.post(ollama_url, json=payload)
    j_res = res.json()
    print(j_res)

    assistant_message = j_res["message"]

    # If there are no tool calls, the model has produced
    # its final response and the agent loop can stop.
    if "tool_calls" not in assistant_message:
        break

    tool_calls = assistant_message["tool_calls"]

    # The model may propose multiple tool calls.
    #
    # For this simple controller, we intentionally execute
    # only the first call per iteration.
    #
    # This guarantees serial execution and ensures that
    # dependent calls can receive actual tool results before continuing.
    accepted_tool_call = tool_calls[0]

    # Add only the accepted tool call to conversation history.
    # This records which action the controller actually allowed.
    messages.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [accepted_tool_call],
        }
    )

    # Extract the tool name and arguments proposed by the model.
    tool_call = accepted_tool_call["function"]
    tool_name = tool_call["name"]
    tool_args = tool_call["arguments"]

    # Controller execution step.
    #
    # Never execute a function directly from an arbitrary model-provided
    # name. Resolve it through the allowed function registry.
    if tool_name in function_registry:
        print(f"Tool Called : {tool_name}")
        func = function_registry[tool_name]
        result = func(**tool_args)
    else:
        result = "Tool not found"

    # Return the actual tool result to the model.
    #
    # On the next loop iteration, the model sees:
    # user request
    # -> accepted assistant tool call
    # -> actual tool result
    #
    # It can then decide whether another tool is needed.
    messages.append(
        {
            "role": "tool",
            "content": str(result),
        }
    )