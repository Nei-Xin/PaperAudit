import pymupdf as fitz

from paperaudit.pdf_parser import parse_pdf


def make_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "A Reliable Paper")
    page.insert_text((72, 100), "The method improves F1 by 3.2 points on Dataset A.")
    data = document.tobytes()
    document.close()
    return data


def test_parse_pdf_preserves_page_and_text() -> None:
    paper = parse_pdf(make_pdf_bytes())

    assert paper.page_count == 1
    assert paper.title == "A Reliable Paper"
    assert any(chunk.page == 1 for chunk in paper.chunks)
    assert any("3.2 points" in chunk.content for chunk in paper.chunks)
    evidence_chunk = next(chunk for chunk in paper.chunks if "3.2 points" in chunk.content)
    assert len(evidence_chunk.rects) == 1
    rect = evidence_chunk.rects[0]
    assert rect.x0 < rect.x1
    assert rect.y0 < rect.y1


def test_parse_pdf_preserves_one_highlight_rect_per_text_line() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(72, 72, 260, 180),
        "This evidence wraps across several lines so the PDF highlight follows each line.",
        fontsize=12,
    )
    pdf_bytes = document.tobytes()
    document.close()

    paper = parse_pdf(pdf_bytes)
    evidence = next(chunk for chunk in paper.chunks if "This evidence" in chunk.content)

    assert len(evidence.rects) >= 2
    assert all(rect.x0 < rect.x1 and rect.y0 < rect.y1 for rect in evidence.rects)


def test_truncated_metadata_title_falls_back_to_complete_first_block() -> None:
    document = fitz.open()
    document.set_metadata({"title": "MLLM-as-a-Judge for Image Safety without"})
    page = document.new_page()
    page.insert_textbox(
        fitz.Rect(72, 72, 500, 140),
        "MLLM-as-a-Judge for Image Safety without\nHuman Labeling",
        fontsize=16,
    )
    pdf_bytes = document.tobytes()
    document.close()

    paper = parse_pdf(pdf_bytes)

    assert paper.title == "MLLM-as-a-Judge for Image Safety without Human Labeling"
