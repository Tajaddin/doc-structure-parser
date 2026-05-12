"""PDF parser — uses pdfminer.six if installed.

PDFs are notoriously unstructured. We extract text via pdfminer and apply a
font-size-based heuristic for headings: the top-N font sizes get mapped to
H1, H2, etc. This is a deliberate trade — accurate enough for most documents,
zero dependency on heavy layout-detection models.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from doc_structure_parser.models import DocumentStructure, Footnote, Heading, Paragraph


@dataclass
class _Span:
    text: str
    size: float
    page: int


def parse_pdf(path: str | Path, *, heading_levels: int = 3) -> DocumentStructure:
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTChar, LTTextContainer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pdfminer.six is not installed. Install with `pip install doc-structure-parser[pdf]`."
        ) from exc

    path = Path(path)
    spans: list[_Span] = []
    for page_num, page_layout in enumerate(extract_pages(str(path)), start=1):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for line in element:
                    sizes = []
                    chars = []
                    for char in line:
                        if isinstance(char, LTChar):
                            sizes.append(char.size)
                            chars.append(char.get_text())
                    if not chars:
                        continue
                    avg_size = sum(sizes) / len(sizes)
                    text = "".join(chars).strip()
                    if text:
                        spans.append(_Span(text=text, size=round(avg_size, 1), page=page_num))

    # Determine the most common font size — that's the "body" size.
    if not spans:
        return DocumentStructure(source=str(path), format="pdf", blocks=[])
    size_counts = Counter(s.size for s in spans)
    body_size, _ = size_counts.most_common(1)[0]

    # Top-N font sizes ABOVE body_size are heading levels H1..HN.
    heading_sizes = sorted({s for s in size_counts if s > body_size + 0.5}, reverse=True)[:heading_levels]
    size_to_level = {sz: i + 1 for i, sz in enumerate(heading_sizes)}

    # Footnote heuristic: a line whose text starts with a small superscript-like number
    # and appears near the bottom of the page. Simpler heuristic: line shorter than
    # body and font smaller. We use *smaller-than-body* font size as a footnote signal.
    footnote_size_threshold = body_size - 0.5

    blocks = []
    para_buf: list[str] = []
    current_page = spans[0].page
    src_index = 0

    def _flush_paragraph() -> None:
        nonlocal src_index
        if para_buf:
            blocks.append(
                Paragraph(text=" ".join(para_buf).strip(), source_index=src_index, page=current_page)
            )
            src_index += 1
            para_buf.clear()

    for span in spans:
        if span.page != current_page:
            _flush_paragraph()
            current_page = span.page

        if span.size in size_to_level:
            _flush_paragraph()
            blocks.append(
                Heading(text=span.text, level=size_to_level[span.size], source_index=src_index, page=current_page)
            )
            src_index += 1
        elif span.size <= footnote_size_threshold and len(span.text) < 200:
            _flush_paragraph()
            blocks.append(
                Footnote(text=span.text, source_index=src_index, page=current_page)
            )
            src_index += 1
        else:
            para_buf.append(span.text)
    _flush_paragraph()

    return DocumentStructure(
        source=str(path),
        format="pdf",
        blocks=blocks,
        metadata={"body_font_size": body_size, "n_spans": len(spans)},
    )
