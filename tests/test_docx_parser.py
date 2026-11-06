"""DOCX parser tests on a document built with python-docx."""

from __future__ import annotations

from pathlib import Path

import pytest

docx = pytest.importorskip("docx")

from doc_structure_parser import parse_docx  # noqa: E402


def _label(path: Path) -> Path:
    doc = docx.Document()
    doc.add_heading("Dosage", level=1)
    doc.add_paragraph("Adults take the dose below.")
    table = doc.add_table(rows=2, cols=2)
    for r, row in enumerate([["dose", "frequency"], ["200mg", "every 4 hours"]]):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    doc.add_paragraph("Children: ask a doctor.")
    doc.add_paragraph("")
    doc.add_heading("Storage", level=2)
    doc.save(str(path))
    return path


def test_tables_keep_their_place_in_document_order(tmp_path: Path) -> None:
    parsed = parse_docx(_label(tmp_path / "label.docx"))
    assert [b.kind for b in parsed.blocks] == [
        "heading",
        "paragraph",
        "table",
        "paragraph",
        "heading",
    ]
    assert [b.source_index for b in parsed.blocks] == [0, 1, 2, 3, 4]


def test_headings_tables_and_text(tmp_path: Path) -> None:
    parsed = parse_docx(_label(tmp_path / "label.docx"))
    assert [(h.text, h.level) for h in parsed.headings()] == [("Dosage", 1), ("Storage", 2)]
    table = parsed.tables()[0]
    assert table.rows == [["dose", "frequency"], ["200mg", "every 4 hours"]]
    assert table.text == "dose: 200mg, frequency: every 4 hours"
    assert [p.text for p in parsed.paragraphs()] == [
        "Adults take the dose below.",
        "Children: ask a doctor.",
    ]
    assert parsed.format == "docx"
