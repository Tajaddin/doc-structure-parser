"""DOCX parser — uses python-docx if installed."""

from __future__ import annotations

from pathlib import Path

from doc_structure_parser.models import DocumentStructure, Heading, Paragraph, Table


def parse_docx(path: str | Path) -> DocumentStructure:
    """Parse a DOCX file into a :class:`DocumentStructure`."""
    try:
        from docx import Document
        from docx.table import Table as DocxTable
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "python-docx is not installed. Install with `pip install doc-structure-parser[docx]`."
        ) from exc

    path = Path(path)
    doc = Document(str(path))
    blocks = []
    src_index = 0

    # The body's paragraphs and tables, interleaved as they appear in the file.
    for item in doc.iter_inner_content():
        if isinstance(item, DocxTable):
            rows = [[cell.text.strip() for cell in row.cells] for row in item.rows]
            if not rows:
                continue
            blocks.append(Table(text=_linearize_table(rows), rows=rows, source_index=src_index))
            src_index += 1
            continue
        text = item.text.strip()
        if not text:
            continue
        style = (item.style.name if item.style else "") or ""
        if style.startswith("Heading"):
            try:
                level = int(style.split()[-1])
            except ValueError:
                level = 1
            level = max(1, min(level, 6))
            blocks.append(Heading(text=text, level=level, source_index=src_index, metadata={"style": style}))
        else:
            blocks.append(Paragraph(text=text, source_index=src_index, metadata={"style": style}))
        src_index += 1

    return DocumentStructure(source=str(path), format="docx", blocks=blocks)


def _linearize_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    out: list[str] = []
    for r in rows[1:]:
        out.append(", ".join(f"{header[i] if i < len(header) else 'col_' + str(i)}: {v}" for i, v in enumerate(r)))
    return "\n".join(out) or "(empty table)"
