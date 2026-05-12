"""Markdown parser — primary parser shipped with the core install.

Markdown is the universal format every team's docs eventually convert to.
Parsing it cleanly into the same :class:`DocumentStructure` as the PDF/DOCX
parsers gives a zero-dependency baseline for tests and a useful first parser
on its own.

Recognized blocks:
* ATX headings: ``# h1`` … ``###### h6``
* Tables: pipe-delimited with separator row
* Footnotes: ``[^marker]: text``
* Everything else: paragraphs (consecutive non-blank lines)
"""

from __future__ import annotations

import re
from pathlib import Path

from doc_structure_parser.models import DocumentStructure, Footnote, Heading, Paragraph, Table

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_FOOTNOTE_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.+)$")


def _split_table_row(line: str) -> list[str]:
    m = _TABLE_ROW_RE.match(line)
    if not m:
        return []
    return [c.strip() for c in m.group(1).split("|")]


def parse_markdown(source: str | Path) -> DocumentStructure:
    """Parse a markdown string or file path into a :class:`DocumentStructure`."""
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).is_file()):
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        source_label = str(path)
    else:
        text = str(source)
        source_label = "(string)"

    lines = text.splitlines()
    blocks = []
    para_buf: list[str] = []
    i = 0
    src_index = 0

    def _flush_paragraph() -> None:
        nonlocal src_index
        if para_buf:
            blocks.append(
                Paragraph(text=" ".join(para_buf).strip(), source_index=src_index)
            )
            src_index += 1
            para_buf.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            _flush_paragraph()
            i += 1
            continue

        # Heading
        m_h = _HEADING_RE.match(stripped)
        if m_h:
            _flush_paragraph()
            level = len(m_h.group(1))
            blocks.append(
                Heading(text=m_h.group(2).strip(), level=level, source_index=src_index)
            )
            src_index += 1
            i += 1
            continue

        # Footnote
        m_f = _FOOTNOTE_RE.match(stripped)
        if m_f:
            _flush_paragraph()
            blocks.append(
                Footnote(text=m_f.group(2).strip(), marker=m_f.group(1), source_index=src_index)
            )
            src_index += 1
            i += 1
            continue

        # Table: header row, then separator row, then data rows.
        if _TABLE_ROW_RE.match(stripped) and i + 1 < len(lines) and _TABLE_SEP_RE.match(lines[i + 1]):
            _flush_paragraph()
            header = _split_table_row(stripped)
            rows: list[list[str]] = [header]
            j = i + 2
            while j < len(lines) and _TABLE_ROW_RE.match(lines[j].strip()):
                rows.append(_split_table_row(lines[j].strip()))
                j += 1
            blocks.append(Table(text=_table_text(rows), rows=rows, source_index=src_index))
            src_index += 1
            i = j
            continue

        # Otherwise → paragraph text
        para_buf.append(stripped)
        i += 1

    _flush_paragraph()

    return DocumentStructure(source=source_label, format="markdown", blocks=blocks)


def _table_text(rows: list[list[str]]) -> str:
    """Linearization of a table for downstream embedding / search."""
    if not rows:
        return ""
    header = rows[0]
    out: list[str] = []
    for r in rows[1:]:
        out.append(", ".join(f"{header[i] if i < len(header) else 'col_' + str(i)}: {v}" for i, v in enumerate(r)))
    return "\n".join(out) or "(empty table)"
