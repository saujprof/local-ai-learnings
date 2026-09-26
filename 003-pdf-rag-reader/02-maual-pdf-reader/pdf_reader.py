import requests
import pypdf
import json
import numpy as np


# Ollama chat API
ollama_url = "http://localhost:11434/api/chat"

# Ollama embedding API
ollama_embedding_url = "http://localhost:11434/api/embed"

# PDF file path
pdf_path = "./northstar_orchard_pilot.pdf"


def generate_embedding(text):
    """
    Generate an embedding vector for the provided text using Ollama.
    """
    payload = {
        "model": "qwen3-embedding:8b",
        "input": text
    }

    res = requests.post(ollama_embedding_url, json=payload)
    res.raise_for_status()

    res = res.json()
    return res["embeddings"][0]


# ---------------------------------------------------------
# STEP 1: Process PDF and create page-aware chunks
# ---------------------------------------------------------

def create_chunks(path):
    """
    Extract text from the PDF and create overlapping, page-aware chunks.

    Chunk size: 500 characters
    Overlap: 100 characters
    """

    pdf = pypdf.PdfReader(path)

    chunks = []
    chunk_size = 500
    chunk_overlap = 100

    for page in pdf.pages:
        text = page.extract_text()

        if not text:
            continue

        text = text.strip()

        print(f"PAGE: {page.page_number}")
        print(f"TEXT LEN: {len(text)}")

        i = 0

        while i <= len(text):

            # If the previous chunk has enough free space, append part of
            # the current page so information crossing a page boundary
            # can stay together.
            last_chunk = chunks[-1] if len(chunks) > 0 else None

            last_chunk_text_len = (
                len(last_chunk["text"])
                if last_chunk
                else None
            )

            remaining_space = (
                chunk_size - last_chunk_text_len
                if last_chunk_text_len
                else None
            )

            if remaining_space and remaining_space >= 200:

                cut_chunk = text[i:i + remaining_space]

                last_chunk["text"] = (
                    last_chunk["text"]
                    + f"\n{cut_chunk}"
                )

                last_chunk["page_end"] = page.page_number

                # Keep overlap between the previous chunk and next chunk.
                i += remaining_space - chunk_overlap

            else:

                # Create a new chunk and move forward while keeping overlap.
                chunk_text = text[i:i + chunk_size]

                chunks.append({
                    "text": chunk_text,
                    "id": len(chunks) + 1,
                    "page_start": page.page_number,
                    "page_end": page.page_number,
                })

                i += chunk_size - chunk_overlap

    return chunks


# ---------------------------------------------------------
# STEP 2: Generate embeddings for every PDF chunk
# ---------------------------------------------------------

def gen_embedding_for_chunks(chunks):
    """
    Generate and attach an embedding vector to every chunk.
    """

    print(f"TOTAL CHUNKS: {len(chunks)}")

    for chunk in chunks:
        embedding = generate_embedding(chunk["text"])
        chunk["embedding"] = embedding

    return chunks


# ---------------------------------------------------------
# STEP 3: Process PDF once and store chunks + embeddings
# ---------------------------------------------------------

def process_pdf(path):
    """
    Chunk the PDF, generate embeddings, and persist them to JSON.
    """

    # Create chunks while preserving page information.
    chunks = create_chunks(path)

    # Generate embedding for every chunk.
    chunks = gen_embedding_for_chunks(chunks)

    # Store chunks and embeddings so they do not need to be regenerated
    # every time a question is asked.
    with open("pdf_chunk_embedding.json", "w") as file:
        json.dump(chunks, file)


# Process the PDF only if stored chunk data is empty.
with open("./pdf_chunk_embedding.json", "r") as file:
    chunks = json.load(file)

    if len(chunks) == 0:
        process_pdf(pdf_path)


# ---------------------------------------------------------
# STEP 4: Manual cosine similarity
# ---------------------------------------------------------
#
# cosine_similarity =
#
#        A · B
#   ----------------
#   |A| × |B|
#
# This manually compares the question embedding with
# each chunk embedding.
#
# FAISS will replace this manual search in V3.
# ---------------------------------------------------------

def get_cosine_similarity(embedding_1, embedding_2):
    """
    Calculate cosine similarity between two embedding vectors.
    """

    dot_product = np.dot(embedding_1, embedding_2)

    embedding_1_magnitude = np.sqrt(
        np.sum(np.square(embedding_1))
    )

    embedding_2_magnitude = np.sqrt(
        np.sum(np.square(embedding_2))
    )

    if embedding_1_magnitude == 0 or embedding_2_magnitude == 0:
        return 0

    return dot_product / (
        embedding_1_magnitude * embedding_2_magnitude
    )


# ---------------------------------------------------------
# STEP 5: Construct context for the LLM
# ---------------------------------------------------------

def construct_content(question, chunks):
    """
    Build the document context sent to the LLM using selected chunks.
    """

    content = "######## DOCUMENT CONTEXT ########\n\n"

    for chunk in chunks:
        print(chunk["id"])

        content += (
            f"######## CHUNK: {chunk['id']} ########\n"
        )

        content += (
            f"######## PAGE START: {chunk['page_start']} "
            f"## PAGE END: {chunk['page_end']} ########\n"
        )

        content += f"{chunk['text']}\n\n"

    content += (
        f"\n######## QUESTION ########\n"
        f"{question}\n"
    )

    return content


def rerank_selected_chunks(question, chunks):
    """
    Ask the LLM to rerank candidate chunks by how relevant and useful
    they are for answering the question.
    """

    content = construct_content(question, chunks)

    messages = [
        {
            "role": "system",
            "content": (
                "Based on the provided question and chunks, rank every chunk "
                "by how relevant and useful it is for answering the question. "
                "Return JSON only. For each chunk include chunk_id, reranked "
                "position, and relevance score from 0 to 100. "
                "Example: "
                "[{\"chunk_id\": \"10\", \"reranked\": 1, \"score\": 78.34}, "
                "{\"chunk_id\": \"9\", \"reranked\": 2, \"score\": 72.34}]"
            )
        },
        {
            "role": "user",
            "content": content
        }
    ]

    payload = {
        "model": "qwen3:8b",
        "stream": False,
        "messages": messages
    }

    res = requests.post(ollama_url, json=payload)
    res.raise_for_status()
    res = res.json()

    print(res)

    reranked_data = json.loads(res["message"]["content"])

    print("RERANKED")
    print(reranked_data)

    return reranked_data


# ---------------------------------------------------------
# STEP 6: Manual RAG query flow
# ---------------------------------------------------------

def agent():
    """
    Run the complete manual RAG flow:
    question embedding -> cosine retrieval -> relative filtering ->
    reranking -> final context -> answer generation.
    """

    question = "What is ORBIT-18?"

    # Generate embedding for the user's question.
    embedded_question = generate_embedding(question)

    # Load previously generated chunks + embeddings.
    with open("./pdf_chunk_embedding.json", "r") as file:
        chunks = json.load(file)

    if len(chunks) == 0:
        return

    # Compare the question embedding against every chunk embedding
    # using manual cosine similarity.
    for chunk in chunks:

        chunk["cosine_similarity"] = float(
            get_cosine_similarity(
                chunk["embedding"],
                embedded_question
            )
        )

        print(
            f"Chunk {chunk['id']} -> "
            f"{chunk['cosine_similarity']}"
        )

    # -----------------------------------------------------
    # Retrieve top-K candidate chunks
    # -----------------------------------------------------

    candidate_k = 8

    ranked_chunks = sorted(
        chunks,
        key=lambda x: float(x["cosine_similarity"]),
        reverse=True
    )

    top_k_chunks = ranked_chunks[:candidate_k]

    # -----------------------------------------------------
    # Relative similarity filtering
    # -----------------------------------------------------
    #
    # Keep candidate chunks whose cosine similarity is at
    # least 60% of the best candidate's similarity.
    #
    # This is a RELATIVE threshold, not an absolute cosine
    # similarity threshold of 0.60.
    # -----------------------------------------------------

    relative_similarity_threshold = 0.6
    max_similarity = top_k_chunks[0]["cosine_similarity"]

    selected_chunks = [
        chunk
        for chunk in top_k_chunks
        if chunk["cosine_similarity"] > (
            relative_similarity_threshold * max_similarity
        )
    ]

    print("Selected chunks id")
    for chunk in selected_chunks:
        print(f"chunk id: {chunk['id']}")

    # -----------------------------------------------------
    # Rerank selected candidates by answer relevance
    # -----------------------------------------------------

    reranked_selected_chunks = rerank_selected_chunks(
        question,
        selected_chunks
    )

    # Keep reranker results above 60, then use only the top-K
    # reranked chunks in the final answer context.
    final_k = 3

    relevant_reranked_chunks = [
        reranked_data
        for reranked_data in reranked_selected_chunks
        if reranked_data["score"] > 60
    ]

    relevant_reranked_chunks = sorted(
        relevant_reranked_chunks,
        key=lambda x: int(x["reranked"])
    )[:final_k]

    final_reranked_selected_chunks = []

    for reranked_data in relevant_reranked_chunks:

        matched_chunk = list(
            filter(
                lambda chunk: int(chunk["id"])
                == int(reranked_data["chunk_id"]),
                selected_chunks
            )
        )

        if matched_chunk:
            final_reranked_selected_chunks.append(
                matched_chunk[0]
            )

    print("Final chunks")
    for chunk in final_reranked_selected_chunks:
        print(f"chunk id: {chunk['id']}")

    # Build the final context using only the top reranked chunks.
    content = construct_content(
        question,
        final_reranked_selected_chunks
    )

    # -----------------------------------------------------
    # STEP 7: Send retrieved context to the LLM
    # -----------------------------------------------------

    payload = {
        "model": "qwen3:8b",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer only from the provided document context. "
                    "If the answer is not supported by the provided chunks, "
                    "say that the information is not available in the document. "
                    "Use chunk and page details as citations when possible."
                )
            },
            {
                "role": "user",
                "content": content
            }
        ]
    }

    res = requests.post(
        ollama_url,
        json=payload
    )

    res.raise_for_status()

    res = res.json()

    print(res)


agent()
