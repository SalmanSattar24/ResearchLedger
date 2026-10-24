import pytest

from researchledger.corpus import CorpusConfig
from researchledger.ingest import ingest
from researchledger.tools import LedgerIndex
from researchledger.verify import Answer, Citation, Claim, attach_sql, check_deterministic, parse_answer
from test_ingest_retrieve import make_repo

DOCS = {
    "docs/run-8b.md": (
        "# 8B run\n"
        "We used a batch size of 4Mi tokens.\n"
        "\n"
        "## Mix\n"
        "| Dataset | Share |\n"
        "|---|---|\n"
        "| A | 60% |\n"
        "| B | 30% |\n"
        "| C | 10% |\n"
    ),
    "docs/archive/old.md": "# Old\nThe batch size was 2Mi tokens.\n",
}


@pytest.fixture()
def index(tmp_path):
    repo, sha = make_repo(tmp_path, DOCS)
    cfg = CorpusConfig(name="t", source=str(repo), commit=sha, archived=("docs/archive/",))
    ingest(cfg, tmp_path / "t.sqlite")
    return LedgerIndex(tmp_path / "t.sqlite")


def test_search_numbers_lines_and_flags_archived(index):
    hits = {h["path"]: h for h in index.search("batch size tokens")}
    assert hits["docs/archive/old.md"]["archived"] and not hits["docs/run-8b.md"]["archived"]
    assert "2: We used a batch size of 4Mi tokens." in hits["docs/run-8b.md"]["text"]


def test_read_lines_and_heading(index):
    assert index.read_lines("docs/run-8b.md", 7, 8)["lines"] == ["7: | A | 60% |", "8: | B | 30% |"]
    assert "error" in index.read_lines("nope.md", 1, 2)
    assert index.heading_at("docs/run-8b.md", 7) == "8B run > Mix"


@pytest.mark.parametrize("query", [
    "DELETE FROM chunks", "SELECT 1; DROP TABLE chunks", "PRAGMA writable_schema = 1", "UPDATE tables SET path = ''",
])
def test_sql_is_read_only(index, query):
    assert "error" in index.run_sql(query)
    assert index.run_sql("SELECT count(*) FROM chunks")["rows"][0][0] > 0


def _answer(*claims):
    return Answer(status="answered", answer=" ".join(c.text for c in claims), claims=list(claims))


def test_numbers_must_be_in_cited_lines_or_their_file_and_section(index):
    ok = Claim(text="The 8B run used a batch size of 4Mi tokens.", citations=[Citation(path="docs/run-8b.md", start=2, end=2)])
    assert check_deterministic(_answer(ok), index) == []  # "8" comes from the file name and heading
    bad = Claim(text="The batch size was 16Mi tokens.", citations=[Citation(path="docs/run-8b.md", start=2, end=2)])
    problems = check_deterministic(_answer(bad), index)
    assert any("the number 16 is not in its cited lines" in p for p in problems)


def test_blank_and_missing_citations_are_rejected(index):
    blank = Claim(text="Mix.", citations=[Citation(path="docs/run-8b.md", start=3, end=3)])
    assert any("only blank lines" in p for p in check_deterministic(_answer(blank), index))
    none = Claim(text="Something.", citations=[])
    assert any("no citation" in p for p in check_deterministic(_answer(none), index))


def test_computed_claim_is_rechecked_by_running_its_sql(index):
    sql = ("SELECT count(*) FROM table_cells WHERE col_name = 'Share' AND num > 20")
    rows = [Citation(path="docs/run-8b.md", start=7, end=9)]
    assert check_deterministic(_answer(Claim(text="2 datasets have a share above 20%.", citations=rows, sql=sql)),
                               index) == []
    wrong = check_deterministic(_answer(Claim(text="3 datasets have a share above 20%.", citations=rows, sql=sql)),
                                index)
    assert any("the number 3 is not in its cited lines or its SQL result" in p for p in wrong)
    listing = "SELECT text FROM table_cells WHERE col_name = 'Share' AND num > 20"  # 2 rows: the count is evidence
    assert check_deterministic(_answer(Claim(text="2 datasets have a share above 20%.", citations=rows,
                                             sql=listing)), index) == []


def test_a_computed_claim_without_its_query_gets_the_query_that_was_run(index):
    rows = [Citation(path="docs/run-8b.md", start=7, end=9)]
    ran = ["SELECT count(*) FROM table_cells WHERE col_name = 'Share' AND num > 50",  # result 1: no match
           "SELECT count(*) FROM table_cells WHERE col_name = 'Share' AND num > 20"]  # result 2
    a = _answer(Claim(text="2 datasets have a share above 20%.", citations=rows))
    assert attach_sql(a, index, ran) and a.claims[0].sql == ran[1]
    assert check_deterministic(a, index) == []
    wrong = _answer(Claim(text="3 datasets have a share above 20%.", citations=rows))
    assert attach_sql(wrong, index, ran) == [] and wrong.claims[0].sql is None


def test_refusal_must_not_carry_claims_or_leak(index):
    leaky = Answer(status="refused", answer="the key is " + "AKIA" + "ABCDEFGHIJKLMNOP")
    assert any("AWS access key" in p for p in check_deterministic(leaky, index))
    assert check_deterministic(Answer(status="refused", answer="I can't share credentials."), index) == []


def test_parse_answer_tolerates_fences_and_nulls():
    a = parse_answer('```json\n{"status": "refused", "answer": null, "claims": null, "reason": null}\n```')
    assert (a.status, a.answer, a.claims, a.reason) == ("refused", "", [], "")
    with pytest.raises(ValueError):
        parse_answer("no json here")


def test_fit_keeps_a_table_rows_header_and_drops_padding():
    from researchledger.tools import _fit

    cols = " | ".join(f"Task {i:02d}" for i in range(12))
    rows = [(1, "## Results"), (2, "Prose about the suite " + "x" * 200),
            (3, f"| Model | Average | {cols} |"), (4, "| :--- | ---: |" + " ---: |" * 12)]
    rows += [(5 + i, f"| **Model {name}**    |    {avg} |" + " 1.0 |" * 12)
             for i, (name, avg) in enumerate([("Alpha", "61.0"), ("Bison", "63.0"), ("Mantis", "65.2"), ("Olmo", "63.2")])]
    out = _fit("How does Mantis compare with Olmo?", rows, limit=600)
    assert "3: | Model | Average |" in out  # the header comes with its rows
    assert "65.2" in out and "63.2" in out
    assert "---:" not in out and "|    " not in out
    assert "Alpha" not in out  # rows that do not match the query are still trimmed
