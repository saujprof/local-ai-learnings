import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.pdf_service import PDFProcessingError, PageText, chunk_pages, extract_pages, process_pdf


def write_pdf(path, texts, password=None):
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    })
    for text in texts:
        page = writer.add_blank_page(width=300, height=300)
        if text:
            page[NameObject('/Resources')] = DictionaryObject({
                NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})
            })
            stream = DecodedStreamObject()
            stream.set_data(f'BT /F1 12 Tf 20 200 Td ({text}) Tj ET'.encode('ascii'))
            page[NameObject('/Contents')] = writer._add_object(stream)
    if password:
        writer.encrypt(password)
    with path.open('wb') as output:
        writer.write(output)


def test_real_pdf_page_references(tmp_path):
    path = tmp_path / 'example.pdf'
    write_pdf(path, ['Refunds within thirty days.', '', 'Contact the support team.'])
    pages = extract_pages(path)
    assert [page.page_number for page in pages] == [1, 2, 3]
    chunks = process_pdf(path, 'doc-1', 'example.pdf', chunk_size=100, overlap=10)
    assert [chunk.text for chunk in chunks] == ['Refunds within thirty days.', 'Contact the support team.']
    assert [(chunk.page_start, chunk.page_end) for chunk in chunks] == [(1, 1), (3, 3)]
    assert [chunk.chunk_id for chunk in chunks] == [0, 1]
    assert all(chunk.document_id == 'doc-1' and chunk.document_name == 'example.pdf' for chunk in chunks)


def test_overlap_and_full_coverage():
    text = 'abcdefghijklmnopqrstuvwxyz'
    chunks = chunk_pages([PageText(1, text)], 'doc', 'file.pdf', 10, 3)
    assert [chunk.text for chunk in chunks] == [text[:10], text[7:17], text[14:24], text[21:]]
    assert chunks[0].text + ''.join(chunk.text[3:] for chunk in chunks[1:]) == text
    assert all(len(chunk.text) <= 10 for chunk in chunks)
    assert len(chunk_pages([PageText(1, '1234567890')], 'doc', 'file.pdf', 10, 0)) == 1


@pytest.mark.parametrize('size, overlap', [(0, 0), (10, -1), (10, 10), (10, 11)])
def test_invalid_chunk_configuration(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([], 'doc', 'file.pdf', size, overlap)


def test_no_text_and_encryption(tmp_path):
    path = tmp_path / 'blank.pdf'
    write_pdf(path, ['', ''])
    with pytest.raises(PDFProcessingError, match='No extractable text'):
        extract_pages(path)
    write_pdf(path, ['Secret'], password='password')
    with pytest.raises(PDFProcessingError, match='Encrypted'):
        extract_pages(path)


def test_unreadable_pdf(tmp_path):
    path = tmp_path / 'broken.pdf'
    path.write_bytes(b'not a PDF')
    with pytest.raises(PDFProcessingError, match='Could not read'):
        extract_pages(path)
    with pytest.raises(PDFProcessingError, match='Could not read'):
        extract_pages(tmp_path / 'missing.pdf')
