import requests
from urllib import parse

# Base URL for Ollama's local HTTP API
llm_base_api_url = "http://localhost:11434/api/"
llm_chat_url = parse.urljoin(llm_base_api_url, "chat")

# Conversation history.
# The system message sets the model's behavior for the conversation.
messages = [
    {
        "role": "system",
        "content": "You are a financial advisor."
    },
]

# Request payload.
# `messages` is the same list object that we keep updating below,
# so every request includes the full conversation history.
payload = {
    "model": "qwen3:8b",
    "messages": messages,
    "stream": False,
}


def start_chat():
    while True:
        user_input = input("User: ")

        # End the local chat loop when the user types "end".
        if user_input.strip().lower() == "end":
            return

        # Add the latest user message to conversation history.
        messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        # Send the complete message history to Ollama.
        res = requests.post(llm_chat_url, json=payload)

        # `/api/chat` returns the model's reply inside:
        # response["message"]["content"]
        assistant_response = res.json()["message"]["content"]
        print(assistant_response)

        # Store the assistant response so it becomes part of
        # the context sent with the next request.
        messages.append(
            {
                "role": "assistant",
                "content": assistant_response
            }
        )


start_chat()