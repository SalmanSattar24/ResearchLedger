"""Turn a file's bytes into the lines that may be indexed, each with its line number in the original file.

Markdown and LaTeX: every line. Notebooks: the source lines of markdown cells only. Code cells and all outputs
are dropped. A notebook's line numbers are those of the raw .ipynb JSON, so a citation points at the file as
stored in git.
"""

from __future__ import annotations

import json
import re

from .leakage import Line


class UnsupportedDocument(Exception):
    """The file cannot be mapped to line ranges reliably; it is skipped and reported, never half-ingested."""


def text_lines(data: bytes) -> list[Line]:
    text = data.decode("utf-8", errors="replace")
    return list(enumerate(text.splitlines(), start=1))


_SOURCE_LIST = re.compile(r'^\s*"source":\s*\[\s*(\],?)?\s*$')
_SOURCE_STR = re.compile(r'^\s*"source":\s*(".*")\s*,?\s*$')


def notebook_markdown_lines(data: bytes) -> list[Line]:
    raw = data.decode("utf-8")
    try:
        cells = json.loads(raw).get("cells", [])
    except json.JSONDecodeError as e:
        raise UnsupportedDocument(f"not valid JSON: {e.msg}") from e
    raw_lines = raw.splitlines()

    # Locate every cell's "source" in the raw text, in order. Jupyter writes one source line per JSON line.
    blocks: list[list[Line]] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if m := _SOURCE_STR.match(line):
            blocks.append([(i + 1, json.loads(m.group(1)))])
        elif m := _SOURCE_LIST.match(line):
            block: list[Line] = []
            if not m.group(1):  # not an empty list on one line
                i += 1
                while i < len(raw_lines) and not raw_lines[i].strip().startswith("]"):
                    item = raw_lines[i].strip().rstrip(",")
                    try:
                        block.append((i + 1, json.loads(item)))
                    except json.JSONDecodeError as e:
                        raise UnsupportedDocument(f"source line {i + 1} is not one JSON string") from e
                    i += 1
            blocks.append(block)
        i += 1

    if len(blocks) != len(cells):
        raise UnsupportedDocument(f"found {len(blocks)} source blocks for {len(cells)} cells")

    out: list[Line] = []
    for cell, block in zip(cells, blocks):
        source = cell.get("source", "")
        expected = "".join(source) if isinstance(source, list) else source
        if "".join(s for _, s in block) != expected:
            raise UnsupportedDocument("cell source does not match its raw lines")
        if cell.get("cell_type") == "markdown":
            out.extend((n, s.rstrip("\n")) for n, s in block)
            if block:  # the line after a cell's source acts as a paragraph break between cells
                out.append((block[-1][0] + 1, ""))
    return out


def document_lines(path: str, data: bytes) -> list[Line]:
    if path.lower().endswith(".ipynb"):
        return notebook_markdown_lines(data)
    return text_lines(data)
