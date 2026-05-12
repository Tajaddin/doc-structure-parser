# doc-structure-parser

> PDF / DOCX / Markdown → a single typed Pydantic structure with **headings, paragraphs, tables, and footnotes** preserved in document order. Zero LLM, optional heavy deps — pdfminer and python-docx are extras you pull in only when you need them.

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE) [![Tests](https://img.shields.io/badge/tests-14%20passing-brightgreen)](#tests) [![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()

## Why this exists

Half the work in any production RAG pipeline is converting messy input documents into clean, embedded-friendly chunks. The vendors are usually [unstructured.io](https://unstructured.io) (great quality, heavyweight install, paid for the good stuff) or hand-rolled regex.

`doc-structure-parser` is a small middle ground:

* **One Pydantic type** for the output across all formats — `DocumentStructure(blocks=[Heading | Paragraph | Table | Footnote])`. Whatever you parse becomes the same shape.
* **Layout-aware splitting per format** — markdown by syntax, DOCX by `Heading N` style, PDF by font-size clustering.
* **Optional heavy deps** — base install is `pydantic` only. PDF and DOCX parsers pull in `pdfminer.six` and `python-docx` only when you opt in.
* **Linearized table text** — every `Table` block has a `.text` field that linearizes `header: value` per row, so the table is embedding-friendly out of the box.

## Quickstart

```bash
pip install -e ".[all]"
```

```python
from doc_structure_parser import parse_markdown, parse_docx, parse_pdf

doc = parse_markdown(
    """
    # Drug label
    ## Indications and usage
    For temporary relief of minor aches.

    | dose | frequency |
    | --- | --- |
    | 200mg | every 4 hours |

    [^1]: Do not exceed 1200mg/day.
    """
)

print([b.kind for b in doc.blocks])
# ['heading', 'heading', 'paragraph', 'table', 'footnote']

print(doc.headings()[0].text)   # 'Drug label'
print(doc.tables()[0].text)     # 'dose: 200mg, frequency: every 4 hours'
print(doc.footnotes()[0].text)  # 'Do not exceed 1200mg/day.'

# Render back to markdown (lossy for table layout but content-faithful):
print(doc.to_markdown())
```

DOCX:

```python
doc = parse_docx("contract.docx")
for h in doc.headings():
    print("-", "  " * (h.level - 1), h.text)
```

PDF:

```python
doc = parse_pdf("paper.pdf", heading_levels=3)
print(f"{len(doc.blocks)} blocks, {len(doc.headings())} headings, {len(doc.tables())} tables")
# Body font size is captured in metadata.
print(doc.metadata["body_font_size"])
```

## Hero features

| Format | What gets recognized | How |
|---|---|---|
| **Markdown** | ATX headings (`# h1` … `###### h6`), pipe tables with separator row, footnotes `[^marker]: text`, paragraphs (consecutive non-blank lines) | Regex-driven syntax parser; no external deps |
| **DOCX** | `Heading 1` … `Heading 6` styles → `Heading.level`, plain paragraphs, all tables linearized to row text | `python-docx` walk over `document.paragraphs` + `document.tables` |
| **PDF** | Font-size clustering — top-N sizes above body → H1..HN; smaller-than-body → footnote; rest → paragraphs | `pdfminer.six` text extraction + character-level font-size aggregation |

Every recognized block lands in the same `DocumentStructure.blocks` list, in document order, with `page` (for PDFs) and `source_index` set so downstream chunkers can reorder safely.

## Models

```python
class DocumentStructure(BaseModel):
    source: str                            # path or "(string)"
    format: Literal["pdf", "docx", "markdown"]
    blocks: list[Heading | Paragraph | Table | Footnote]
    metadata: dict

class Heading(BaseModel):
    kind: Literal[BlockKind.HEADING]
    text: str
    level: int                             # 1..6
    page: int | None
    source_index: int
    metadata: dict

class Table(BaseModel):
    kind: Literal[BlockKind.TABLE]
    text: str                              # linearized header:value lines
    rows: list[list[str]]                  # parsed cells (rows[0] = header)
    page: int | None
    source_index: int

class Footnote(BaseModel):
    kind: Literal[BlockKind.FOOTNOTE]
    text: str
    marker: str                            # e.g. "1", "*", "†"
    page: int | None
```

All blocks use Pydantic v2 `model_config(extra="forbid")` so a typo in the parser surfaces as a validation error, not a silent miss.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

```
14 passed in 0.20s
```

Coverage:

* Markdown heading levels, paragraph join, table parsing, footnote markers, mixed-document order preservation
* `to_markdown()` round-trip of headings + paragraphs
* `Heading.level` rejects out-of-range
* `Table.n_columns` and `.n_data_rows` math
* `DocumentStructure` view methods (`headings()`, `tables()`, `footnotes()`)

PDF and DOCX parsers are exercised by smoke imports — full end-to-end tests on those formats need real binary fixtures and are out of scope for v0.1.

## Project layout

```
.
├── src/doc_structure_parser/
│   ├── models.py             # DocumentStructure + Heading/Paragraph/Table/Footnote
│   └── parsers/
│       ├── markdown_parser.py    # always-available, no extra deps
│       ├── docx_parser.py        # needs python-docx
│       └── pdf_parser.py         # needs pdfminer.six
└── tests/                    # 14 pytest cases (markdown + models)
```

## Limitations

**Setext-style markdown headings not supported.** Only ATX (`#`, `##`, …). Setext (`Title\n=====`) is rarer in produced markdown and the parser treats `===` as text. Could add detection in v0.2.

**PDF heading detection is heuristic.** Font-size clustering works on well-formatted papers but can collapse two heading levels when a document uses italic vs. bold for distinction. The escape hatch is `heading_levels=N` to cap the number of recognized levels.

**Tables in PDFs aren't extracted as tables.** PDF table detection is a Hard Problem in itself — solutions like Camelot, Tabula, or unstructured.io's hi-res model exist but are heavy. `pdf_parser` returns table content as paragraph text; for real PDF tables, route through Camelot or unstructured.io and re-wrap in `Table` blocks downstream.

**No image extraction.** All parsers drop images. RAG over multimodal documents needs a separate path (e.g., embed page screenshots via a vision model).

**No streaming.** Documents are parsed in-memory. For 10MB+ documents this is fine; for very large books, a chunked parser would be a natural v0.2 extension.

## License

MIT — see [LICENSE](LICENSE).
