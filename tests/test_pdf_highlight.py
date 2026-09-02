import base64

import pymupdf

from paperaudit.pdf_parser import parse_pdf
from paperaudit.ui.learning import _rect_coordinates, _render_pdf_page
from paperaudit.ui.pdf_selector import _page_payload, _render_scale_for_zoom


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


def test_pdf_selector_uses_adaptive_render_scale() -> None:
    assert _render_scale_for_zoom(50) == 2.5
    assert _render_scale_for_zoom(100) == 2.5
    assert _render_scale_for_zoom(110) == 3.0
    assert _render_scale_for_zoom(130) == 3.0
    assert _render_scale_for_zoom(140) == 3.5
    assert _render_scale_for_zoom(180) == 3.5


def test_pdf_selector_payload_uses_high_resolution_png() -> None:
    pdf_bytes = _make_pdf()
    payload = _page_payload(pdf_bytes, 1, 2.5)
    png_bytes = base64.b64decode(payload["image_url"].partition(",")[2])
    pixmap = pymupdf.Pixmap(png_bytes)

    assert pixmap.width >= payload["page_width"] * 2.5
    assert pixmap.height >= payload["page_height"] * 2.5
