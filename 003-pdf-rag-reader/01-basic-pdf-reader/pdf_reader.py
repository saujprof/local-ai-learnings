import requests
import pypdf


# Ollama chat API
ollama_url = "http://localhost:11434/api/chat"

# PDF file path
pdf_path = "./northstar_orchard_pilot.pdf"


def extract_pdf(path: str):
    """
    Extract all text from the PDF.

    V1 intentionally loads the COMPLETE document into memory
    and sends the COMPLETE document to the LLM.

    Later versions will replace this with chunking + retrieval.
    """

    if not path:
        return ""

    pdf = pypdf.PdfReader(path)

    content = ""

    for page in pdf.pages:
        page_text = page.extract_text()

        # extract_text() can theoretically return None
        if page_text:
            content += page_text
            content += "\n\n"

    return content


# ---------------------------------------------------------
# STEP 1: Load the document
# ---------------------------------------------------------

pdf_content = extract_pdf(pdf_path)

print("PDF loaded")
print("Extracted characters:", len(pdf_content))


# ---------------------------------------------------------
# STEP 2: Document context
# ---------------------------------------------------------
#
# The document is kept as a separate message because conceptually
# the document remains the same while the user's question changes.
#
# In this V1 implementation, every API request still sends the
# complete messages list again. Ollama / the LLM does not remember
# the previous HTTP request automatically.
#
# So even though the PDF is logically "static context", it is still
# included in every request in this simple implementation.
#

document_context = f"""
DOCUMENT START

{pdf_content}

DOCUMENT END
"""


# ---------------------------------------------------------
# STEP 3: Build conversation
# ---------------------------------------------------------
#
# System message defines how we want the model to behave.
#
# The PDF is provided once in the message history.
#
# Questions can then be changed independently without changing
# how the PDF was extracted or represented.
#

messages = [
    {
        "role": "system",
        "content": (
            "Answer questions using only the provided document. "
            "If the document does not contain the answer, say that "
            "the information is not available in the document."
        ),
    },
    {
        "role": "user",
        "content": document_context,
    },
]


# ---------------------------------------------------------
# STEP 4: Ask a question
# ---------------------------------------------------------

question = "Summarise the PDF content"

messages.append(
    {
        "role": "user",
        "content": question,
    }
)


# ---------------------------------------------------------
# STEP 5: Send everything to Ollama
# ---------------------------------------------------------
#
# Important:
#
# HTTP requests are stateless.
#
# Ollama does NOT remember that we sent the PDF earlier.
# The complete message history is sent again with every request.
#
# Later we will see why repeatedly sending a large document becomes
# expensive and eventually hits the model's context-window limit.
#

payload = {
    "model": "qwen3:8b",
    "messages": messages,
    "stream": False,
}

response = requests.post(ollama_url, json=payload)
response.raise_for_status()

result = response.json()


# ---------------------------------------------------------
# STEP 6: Print only the assistant's answer
# ---------------------------------------------------------

assistant_message = result["message"]

print("\nQuestion:")
print(question)

print("\nAnswer:")
print(assistant_message["content"])