import requests

from tools import search_flights, search_hotels, calculate_cost

# Ollama local chat API endpoint.
ollama_url = "http://localhost:11434/api/chat"


def plan_trip(question):
    """
    Create a structured workflow plan for the user's travel request.

    Important:
    - This function only asks the LLM to PLAN tool usage.
    - It does not execute any tool.
    - The returned plan is intended to be machine-readable by a future executor.
    """

    # System instructions define the planner's responsibility
    # and the exact JSON structure it should return.
    system_content = """
    You are a workflow planner for an agentic flow.
    You will provide a clean plan of action to achieve the user's request.
    You will not execute or perform any action.

    Do not invent or fill missing gaps in the request.

    Respond in JSON format only so the plan executor can read it.

    Exact structure to follow:

    [
      {
        "step_id": 0,
        "tool": "tool name",
        "arguments": {}
      }
    ]

    Rules:
    - Give every step a unique sequential ID.
    - Use only provided tools.
    - Use exact tool and parameter names.
    - Every explicitly requested action must appear in the plan when a tool supports it.
    - Use only tools necessary for the user's request.
    - Do not invent or assume missing/incomplete information from the user's request.
      Example: if "year" is not explicitly provided, do not infer it.
    - Prefer explicit user values over inferred values.
    - Derive values only when unambiguous.
    - If a required value is unknown, use null.
    - Do not execute tools.
    """

    # Provide the planner with the available tool definitions
    # and the user's request as normal context.
    #
    # We intentionally do NOT pass these through Ollama's `tools`
    # parameter because this stage is about planning, not tool calling.
    user_content = f"""
    Tools available:
    {[search_hotels, search_flights, calculate_cost]}

    User request:
    {question}
    """

    messages = [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": user_content
        }
    ]

    # Ask the LLM to return the structured plan.
    payload = {
        "model": "qwen3:8b",
        "messages": messages,
        "stream": False
    }

    # Send the planning request to Ollama.
    res = requests.post(ollama_url, json=payload)

    # Parse and print the raw Ollama response.
    # In later stages, we will extract and validate the JSON plan.
    j_res = res.json()
    print(j_res)


# Example request used to test structured planning.
plan_trip(
    "I want to travel from Kanpur to Delhi on 25th of october "
    "for 4 days and then return on 29th"
)