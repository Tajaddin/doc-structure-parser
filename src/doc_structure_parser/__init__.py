"""PDF/DOCX → typed Pydantic with layout-aware splitting."""

from doc_structure_parser.models import (
    Block,
    BlockKind,
    DocumentStructure,
    Footnote,
    Heading,
    Paragraph,
    Table,
)
from doc_structure_parser.parsers.docx_parser import parse_docx
from doc_structure_parser.parsers.markdown_parser import parse_markdown
from doc_structure_parser.parsers.pdf_parser import parse_pdf

__version__ = "0.1.0"

__all__ = [
    "DocumentStructure",
    "Block",
    "BlockKind",
    "Heading",
    "Paragraph",
    "Table",
    "Footnote",
    "parse_docx",
    "parse_markdown",
    "parse_pdf",
]
