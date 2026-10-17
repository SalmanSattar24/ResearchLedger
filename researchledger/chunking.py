"""Split a document into section-aware chunks that keep exact line ranges.

A chunk never crosses a heading and never splits a paragraph: sections are cut into blocks at blank lines, and
blocks are packed into chunks of at most MAX_LINES lines (a single larger block, such as a table, stays whole).
A chunk's text is exactly the indexed lines in its range, blank lines included, and `line_numbers` maps each text
line to its line in the original file. (One chunk per table row was tried on 17 Oct 2026 and lowered recall on
the public set, so it was dropped.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .leakage import Line

MAX_LINES = 30

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_TEX_HEADING = re.compile(r"^\s*\\(part|chapter|section|subsection|subsubsection|paragraph)\*?\{(.+?)\}")
_TEX_LEVEL = {"part": 1, "chapter": 2, "section": 3, "subsection": 4, "subsubsection": 5, "paragraph": 6}


@dataclass(frozen=True)
class Chunk:
    path: str
    start_line: int
    end_line: int
    heading: str  # "Top > Sub > Subsub"; empty before the first heading
    text: str
    line_numbers: tuple[int, ...]


def _heading(path: str, line: str, in_fence: bool) -> tuple[int, str] | None:
    if in_fence:
        return None
    if path.lower().endswith(".tex"):
        if m := _TEX_HEADING.match(line):
            return _TEX_LEVEL[m.group(1)], m.group(2).strip()
        return None
    if m := _MD_HEADING.match(line):
        return len(m.group(1)), m.group(2).strip()
    return None


def sections(path: str, lines: list[Line]) -> list[tuple[str, list[Line]]]:
    out: list[tuple[str, list[Line]]] = []
    stack: list[tuple[int, str]] = []
    current: list[Line] = []
    heading = ""
    in_fence = False
    for n, line in lines:
        h = _heading(path, line, in_fence)
        if _FENCE.match(line):
            in_fence = not in_fence
        if h:
            if current:
                out.append((heading, current))
            level, title = h
            stack = [(lv, t) for lv, t in stack if lv < level] + [(level, title)]
            heading = " > ".join(t for _, t in stack)
            current = []
        current.append((n, line))
    if current:
        out.append((heading, current))
    return out


def _blocks(lines: list[Line]) -> list[list[Line]]:
    blocks: list[list[Line]] = []
    current: list[Line] = []
    in_fence = False
    for n, line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append((n, line))
    if current:
        blocks.append(current)
    return blocks


def chunk_document(path: str, lines: list[Line], max_lines: int = MAX_LINES) -> list[Chunk]:
    chunks: list[Chunk] = []
    for heading, section in sections(path, lines):
        packed: list[list[Line]] = []

        def flush() -> None:
            if packed:
                start, end = packed[0][0][0], packed[-1][-1][0]
                span = [(n, s) for n, s in section if start <= n <= end]
                text = "\n".join(s for _, s in span)
                chunks.append(Chunk(path, start, end, heading, text, tuple(n for n, _ in span)))
                packed.clear()

        for block in _blocks(section):
            if packed and block[-1][0] - packed[0][0][0] + 1 > max_lines:
                flush()
            packed.append(block)
        flush()
    return chunks
