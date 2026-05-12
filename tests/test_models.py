"""Model tests."""

from __future__ import annotations

import pytest

from doc_structure_parser.models import BlockKind, DocumentStructure, Heading, Paragraph, Table


def test_heading_rejects_invalid_level() -> None:
    with pytest.raises(Exception):
        Heading(text="x", level=0)
    with pytest.raises(Exception):
        Heading(text="x", level=7)


def test_table_n_columns_and_data_rows() -> None:
    t = Table(text="-", rows=[["a", "b"], ["1", "2"], ["3", "4"]])
    assert t.n_columns == 2
    assert t.n_data_rows == 2


def test_table_empty_rows() -> None:
    t = Table(text="-", rows=[])
    assert t.n_columns == 0
    assert t.n_data_rows == 0


def test_document_structure_views() -> None:
    doc = DocumentStructure(
        source="-", format="markdown",
        blocks=[
            Heading(text="h", level=1),
            Paragraph(text="body"),
            Heading(text="h2", level=2),
        ],
    )
    assert len(doc.headings()) == 2
    assert len(doc.paragraphs()) == 1
    assert doc.headings()[0].text == "h"


def test_document_structure_to_markdown_includes_levels() -> None:
    doc = DocumentStructure(
        source="-", format="markdown",
        blocks=[Heading(text="h", level=2), Paragraph(text="body")],
    )
    md = doc.to_markdown()
    assert md.startswith("## h")
    assert "body" in md
