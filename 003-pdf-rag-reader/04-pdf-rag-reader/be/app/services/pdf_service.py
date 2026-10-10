"""Extract text and build overlapping chunks within individual PDF pages.

Character-based sizing is intentional for V4. Keeping each chunk within one page
makes citation metadata exact. OCR is not included.
"""
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


class PDFProcessingError(ValueError):
    """A PDF cannot provide text for indexing."""


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class PDFChunk:
    document_id: str
    document_name: str
    chunk_id: int
    page_start: int
    page_end: int
    text: str


def extract_pages(path: Path) -> list[PageText]:
    try:
        with path.open('rb') as content:
            reader = PdfReader(content)
            if reader.is_encrypted:
                raise PDFProcessingError('Encrypted PDFs are not supported.')
            pages = [
                PageText(number, ' '.join((page.extract_text() or '').split()))
                for number, page in enumerate(reader.pages, start=1)
            ]
    except PDFProcessingError:
        raise
    except Exception as exc:
        raise PDFProcessingError('Could not read text from this PDF.') from exc
    if not any(page.text for page in pages):
        raise PDFProcessingError('No extractable text found. Scanned PDFs require OCR, which is not supported yet.')
    return pages


def chunk_pages(
    pages: list[PageText], document_id: str, document_name: str,
    chunk_size: int = 1000, overlap: int = 150,
) -> list[PDFChunk]:
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError('chunk_size must be positive and overlap must be between 0 and chunk_size - 1.')
    if not document_id or not document_name:
        raise ValueError('Document ID and name are required.')
    chunks = []
    for page in pages:
        if page.page_number < 1:
            raise ValueError('Page numbers must be positive.')
        text = page.text.strip()
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(PDFChunk(document_id, document_name, len(chunks),
                                       page.page_number, page.page_number, piece))
            if end == len(text):
                break
            start = end - overlap
    return chunks


def process_pdf(
    path: Path, document_id: str, document_name: str,
    chunk_size: int = 1000, overlap: int = 150,
) -> list[PDFChunk]:
    """Return chunks for ingestion; does not update registry or call embeddings."""
    return chunk_pages(extract_pages(path), document_id, document_name, chunk_size, overlap)
