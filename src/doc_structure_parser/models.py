"""Pydantic models for the structured document representation.

A :class:`DocumentStructure` is an ordered list of :class:`Block`s. Each block
is one of: ``Heading``, ``Paragraph``, ``Table``, ``Footnote``. Every block
carries provenance — page number (for paginated formats), source line/index,
and free-form metadata.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class BlockKind(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FOOTNOTE = "footnote"


class _BaseBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: BlockKind
    text: str
    page: int | None = None
    source_index: int = 0
    metadata: dict = Field(default_factory=dict)


class Heading(_BaseBlock):
    kind: Literal[BlockKind.HEADING] = BlockKind.HEADING
    level: int = Field(ge=1, le=6, default=1)


class Paragraph(_BaseBlock):
    kind: Literal[BlockKind.PARAGRAPH] = BlockKind.PARAGRAPH


class Table(_BaseBlock):
    """``rows`` is the parsed table as list-of-list-of-strings (header in [0])."""

    kind: Literal[BlockKind.TABLE] = BlockKind.TABLE
    rows: list[list[str]] = Field(default_factory=list)

    @property
    def n_columns(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    @property
    def n_data_rows(self) -> int:
        return max(0, len(self.rows) - 1)


class Footnote(_BaseBlock):
    kind: Literal[BlockKind.FOOTNOTE] = BlockKind.FOOTNOTE
    marker: str = ""   # e.g. "1", "*", "†"


Block = Annotated[
    Union[Heading, Paragraph, Table, Footnote],
    Field(discriminator="kind"),
]


class DocumentStructure(BaseModel):
    """The full structured representation of one parsed document."""

    model_config = ConfigDict(extra="forbid")
    source: str
    format: Literal["pdf", "docx", "markdown"]
    blocks: list[Block] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    # Convenience views ------------------------------------------------
    def headings(self) -> list[Heading]:
        return [b for b in self.blocks if isinstance(b, Heading)]

    def paragraphs(self) -> list[Paragraph]:
        return [b for b in self.blocks if isinstance(b, Paragraph)]

    def tables(self) -> list[Table]:
        return [b for b in self.blocks if isinstance(b, Table)]

    def footnotes(self) -> list[Footnote]:
        return [b for b in self.blocks if isinstance(b, Footnote)]

    def to_markdown(self) -> str:
        """Render back to a readable markdown approximation (lossy for tables)."""
        lines: list[str] = []
        for b in self.blocks:
            if isinstance(b, Heading):
                lines.append("#" * b.level + " " + b.text)
            elif isinstance(b, Paragraph):
                lines.append(b.text)
            elif isinstance(b, Table):
                if b.rows:
                    lines.append("| " + " | ".join(b.rows[0]) + " |")
                    lines.append("| " + " | ".join(["---"] * b.n_columns) + " |")
                    for r in b.rows[1:]:
                        lines.append("| " + " | ".join(r) + " |")
            elif isinstance(b, Footnote):
                lines.append(f"[^{b.marker or '*'}]: {b.text}")
            lines.append("")
        return "\n".join(lines).strip()
