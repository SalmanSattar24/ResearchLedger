import json

import pytest

from researchledger.chunking import chunk_document
from researchledger.documents import UnsupportedDocument, notebook_markdown_lines, text_lines
from researchledger.tables import extract_tables, to_number

MD = """# Report
intro line

## Phase 1
para one
still para one

| Dataset | Share |
|---|---|
| A | 92.6% |
| B | **6.1%** |

```
# not a heading
```

## Phase 2
last
"""


def test_chunks_follow_headings_and_keep_line_ranges():
    chunks = chunk_document("r.md", text_lines(MD.encode()))
    assert [(c.heading, c.start_line, c.end_line) for c in chunks] == [
        ("Report", 1, 2),
        ("Report > Phase 1", 4, 15),
        ("Report > Phase 2", 17, 18),
    ]
    assert "# not a heading" in chunks[1].text


def test_chunk_text_is_exactly_the_lines_in_its_range():
    lines = text_lines(MD.encode())
    for c in chunk_document("r.md", lines):
        assert c.line_numbers == tuple(range(c.start_line, c.end_line + 1))
        assert c.text.split("\n") == [t for n, t in lines if c.start_line <= n <= c.end_line]


def test_long_sections_split_at_blank_lines_without_breaking_a_table():
    chunks = chunk_document("r.md", text_lines(MD.encode()), max_lines=4)
    phase1 = [(c.start_line, c.end_line) for c in chunks if c.heading == "Report > Phase 1"]
    assert phase1 == [(4, 6), (8, 11), (13, 15)]


def test_long_sections_split_at_blank_lines():
    md = "# T\n" + "\n".join(f"para {i}\nmore {i}\n" for i in range(4))
    chunks = chunk_document("t.md", text_lines(md.encode()), max_lines=4)
    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 3), (5, 6), (8, 9), (11, 12)]


def test_markdown_table_is_parsed_with_line_numbers_and_numbers():
    (t,) = extract_tables("r.md", text_lines(MD.encode()))
    assert (t.start_line, t.end_line, t.heading, t.columns) == (8, 11, "Report > Phase 1", ["Dataset", "Share"])
    assert t.rows == [(10, ["A", "92.6%"]), (11, ["B", "6.1%"])]
    assert [to_number(c) for _, (_, c) in t.rows] == [92.6, 6.1]
    assert to_number("1,159") == 1159 and to_number("≈0.02") == 0.02 and to_number("n/a") is None


def notebook(cells):
    nb = {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    return json.dumps(nb, indent=1).encode()


def test_notebook_keeps_markdown_cells_only_with_raw_line_numbers():
    data = notebook([
        {"cell_type": "markdown", "metadata": {}, "source": ["# Title\n", "text\n"]},
        {"cell_type": "code", "execution_count": 1, "metadata": {}, "outputs": [{"output_type": "stream",
         "name": "stdout", "text": ["SECRET OUTPUT\n"]}], "source": ["print(1)\n"]},
        {"cell_type": "markdown", "metadata": {}, "source": "single string cell"},
    ])
    lines = notebook_markdown_lines(data)
    raw = data.decode().splitlines()
    texts = [t for _, t in lines if t]
    assert texts == ["# Title", "text", "single string cell"]
    for n, t in lines:
        if t:
            assert json.dumps(t)[1:-1] in raw[n - 1]
    assert all("SECRET OUTPUT" not in t and "print(1)" not in t for _, t in lines)


def test_notebook_that_cannot_be_mapped_is_refused():
    with pytest.raises(UnsupportedDocument):
        notebook_markdown_lines(b'{"cells": [{"cell_type": "markdown", "source": ["a\\n", "b"]}]}')
