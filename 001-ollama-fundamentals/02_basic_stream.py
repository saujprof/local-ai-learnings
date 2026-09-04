from urllib import parse
import requests
import json

# Ollama LLM API URL
llm_base_api_url = "http://localhost:11434/api/"
llm_generate_url = parse.urljoin(llm_base_api_url, "generate")

# Request payload
payload = {
    "model": "qwen3:8b",
    "prompt": "What is the capital of Germany ?",
    "stream": True,
}

# With streaming enabled, Ollama does not wait for the full
# generated response before sending data back.
# Instead, it sends multiple JSON chunks over the same HTTP response.
#
# Each chunk may contain a small piece of generated text.
# Some models/runtimes may also expose reasoning/thinking separately.

# Send request
res = requests.post(llm_generate_url, json=payload)

# Read each streamed JSON chunk as it arrives
for line in res.iter_lines():
    if line:
        chunk = json.loads(line)
        print(chunk["response"])
