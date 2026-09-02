import pymupdf

from paperaudit.pdf_parser import parse_pdf
from paperaudit.ui.learning import _rect_coordinates, _render_pdf_page


def _make_pdf() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 90), "Evidence to highlight in the PDF page.")
    data = document.tobytes()
    document.close()
    return data


def test_render_pdf_page_adds_local_evidence_highlight() -> None:
    pdf_bytes = _make_pdf()
    paper = parse_pdf(pdf_bytes)
    evidence = next(chunk for chunk in paper.chunks if "Evidence to highlight" in chunk.content)

    plain = _render_pdf_page(pdf_bytes, 1)
    highlighted = _render_pdf_page(pdf_bytes, 1, _rect_coordinates(evidence.rects))

    assert evidence.rects
    assert highlighted != plain
    assert pymupdf.Pixmap(highlighted).width == pymupdf.Pixmap(plain).width
