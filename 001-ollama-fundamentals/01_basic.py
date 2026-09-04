from urllib import parse
import requests

# Base URL for Ollama's local HTTP API
llm_base_api_url = "http://localhost:11434/api/"
llm_generate_url = parse.urljoin(llm_base_api_url, "generate")

# Request payload sent to the model
payload = {
    "model": "qwen3:8b",
    "prompt": "What is the capital of Germany ?",
    "stream": False,
}

# With stream=False, Ollama waits until generation is complete
# and returns the result in a single JSON response.

# Send the HTTP POST request to Ollama
res = requests.post(llm_generate_url, json=payload)

# For /api/generate, the generated text is available
# in the "response" field of the returned JSON object.
print(res.json()["response"])
