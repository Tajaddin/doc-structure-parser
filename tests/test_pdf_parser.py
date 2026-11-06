"""PDF parser tests on a small PDF written by hand (Helvetica, no embedded fonts)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pdfminer")

from doc_structure_parser import parse_pdf  # noqa: E402


def _pdf(pages: list[list[tuple[float, str]]]) -> bytes:
    """A PDF with one text line per (font size, text), laid out top-down per page."""
    n = len(pages)
    page_ids = [3 + i for i in range(n)]
    content_ids = [3 + n + i for i in range(n)]
    font_id = 3 + 2 * n
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (" ".join(f"{i} 0 R" for i in page_ids).encode(), n),
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for page_id, content_id, lines in zip(page_ids, content_ids, pages, strict=True):
        y, ops = 740.0, []
        for size, text in lines:
            ops.append(f"BT /F1 {size} Tf 72 {y:.1f} Td ({text}) Tj ET")
            y -= size * 2
        stream = "\n".join(ops).encode("latin-1")
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (font_id, content_id)
        )
        objects[content_id] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (obj_id, objects[obj_id])
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for obj_id in sorted(objects):
        out += b"%010d 00000 n \n" % offsets[obj_id]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


@pytest.fixture
def label_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "label.pdf"
    path.write_bytes(
        _pdf(
            [
                [
                    (24, "Drug label"),
                    (11, "For temporary relief of minor aches."),
                    (16, "Usage"),
                    (11, "Take one tablet every four hours."),
                    (11, "Do not exceed six tablets a day."),
                    (8, "1 Store below 25 C."),
                ],
                [(11, "Keep out of reach of children.")],
            ]
        )
    )
    return path


def test_font_sizes_map_to_headings_body_and_footnotes(label_pdf: Path) -> None:
    parsed = parse_pdf(label_pdf)
    assert [(b.kind, b.text) for b in parsed.blocks] == [
        ("heading", "Drug label"),
        ("paragraph", "For temporary relief of minor aches."),
        ("heading", "Usage"),
        ("paragraph", "Take one tablet every four hours. Do not exceed six tablets a day."),
        ("footnote", "1 Store below 25 C."),
        ("paragraph", "Keep out of reach of children."),
    ]
    assert [h.level for h in parsed.headings()] == [1, 2]
    assert parsed.metadata["body_font_size"] == 11.0


def test_pages_and_source_order(label_pdf: Path) -> None:
    parsed = parse_pdf(label_pdf)
    assert [b.page for b in parsed.blocks] == [1, 1, 1, 1, 1, 2]
    assert [b.source_index for b in parsed.blocks] == list(range(6))


def test_heading_levels_caps_the_number_of_levels(label_pdf: Path) -> None:
    parsed = parse_pdf(label_pdf, heading_levels=1)
    assert [h.text for h in parsed.headings()] == ["Drug label"]
    assert any("Usage" in p.text for p in parsed.paragraphs())  # demoted, not dropped
