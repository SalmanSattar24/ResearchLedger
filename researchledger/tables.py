"""Parse Markdown tables into typed rows, each with its line number, for the SQL agent."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .chunking import sections
from .leakage import Line

_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
_NUMBER = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class Table:
    path: str
    start_line: int
    end_line: int
    heading: str
    columns: list[str]
    rows: list[tuple[int, list[str]]]  # (line number, cells)


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def clean_cell(cell: str) -> str:
    """Strip Markdown emphasis, code ticks and HTML line breaks; keep the visible text."""
    cell = re.sub(r"<br\s*/?>", " ", cell)
    cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)  # links -> their text
    return cell.replace("**", "").replace("`", "").strip()


def to_number(cell: str) -> float | None:
    """'92.6%' -> 92.6, '1,159' -> 1159, '\u22480.02' -> 0.02, '**66.6**' -> 66.6; anything else -> None."""
    s = clean_cell(cell).replace(",", "").replace("\u2248", "").replace("~", "").rstrip("%\u2020").strip()
    s = s.replace("\u2011", "-").replace("\u2212", "-")
    return float(s) if _NUMBER.match(s) else None


def extract_tables(path: str, lines: list[Line]) -> list[Table]:
    tables: list[Table] = []
    for heading, section in sections(path, lines):
        i = 0
        while i + 1 < len(section):
            n, line = section[i]
            if line.lstrip().startswith("|") and _SEPARATOR.match(section[i + 1][1]):
                columns = [clean_cell(c) for c in _cells(line)]
                rows = []
                j = i + 2
                while j < len(section) and section[j][1].lstrip().startswith("|"):
                    rows.append((section[j][0], [clean_cell(c) for c in _cells(section[j][1])]))
                    j += 1
                end = section[j - 1][0]
                tables.append(Table(path, n, end, heading, columns, rows))
                i = j
            else:
                i += 1
    return tables
