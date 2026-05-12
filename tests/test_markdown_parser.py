"""Markdown parser tests."""

from __future__ import annotations

import pytest

from doc_structure_parser import BlockKind, parse_markdown


def test_heading_levels() -> None:
    doc = parse_markdown("# h1\n## h2\n### h3\n#### h4")
    headings = doc.headings()
    assert [h.level for h in headings] == [1, 2, 3, 4]
    assert headings[0].text == "h1"


def test_paragraphs_join_consecutive_lines() -> None:
    doc = parse_markdown("first line\nsecond line\n\nseparate paragraph")
    paragraphs = doc.paragraphs()
    assert len(paragraphs) == 2
    assert paragraphs[0].text == "first line second line"
    assert paragraphs[1].text == "separate paragraph"


def test_table_with_header_and_data_rows() -> None:
    md = """
| name | age |
| --- | --- |
| alice | 30 |
| bob | 42 |
""".strip()
    doc = parse_markdown(md)
    tables = doc.tables()
    assert len(tables) == 1
    t = tables[0]
    assert t.rows[0] == ["name", "age"]
    assert t.n_columns == 2
    assert t.n_data_rows == 2
    assert "alice" in t.text and "30" in t.text


def test_footnote_recognized() -> None:
    doc = parse_markdown("body[^1]\n\n[^1]: the footnote text")
    fns = doc.footnotes()
    assert len(fns) == 1
    assert fns[0].marker == "1"
    assert fns[0].text == "the footnote text"


def test_mixed_document_block_order_preserved() -> None:
    md = """
# Title

intro paragraph.

## Section A

body of A.

| col1 | col2 |
| --- | --- |
| a | b |

[^1]: note
""".strip()
    doc = parse_markdown(md)
    kinds = [b.kind for b in doc.blocks]
    assert kinds == [
        BlockKind.HEADING,    # Title
        BlockKind.PARAGRAPH,  # intro paragraph
        BlockKind.HEADING,    # Section A
        BlockKind.PARAGRAPH,  # body of A
        BlockKind.TABLE,
        BlockKind.FOOTNOTE,
    ]


def test_to_markdown_round_trips_headings_and_paragraphs() -> None:
    doc = parse_markdown("# Title\n\nbody.")
    re_md = doc.to_markdown()
    assert "# Title" in re_md
    assert "body." in re_md


def test_empty_input_returns_empty_blocks() -> None:
    doc = parse_markdown("")
    assert doc.blocks == []
    assert doc.headings() == []


def test_setext_style_not_required_atx_only() -> None:
    """We only support ATX headings (# ...), not setext (=== underlines)."""
    doc = parse_markdown("Setext-like\n===========")
    # The === line is a "paragraph" continuation since we don't recognize setext.
    paragraphs = doc.paragraphs()
    assert any("===" in p.text for p in paragraphs)


def test_footnote_with_named_marker() -> None:
    doc = parse_markdown("[^note]: see appendix A")
    fns = doc.footnotes()
    assert len(fns) == 1
    assert fns[0].marker == "note"
