import yaml

from researchledger.corpus import CorpusConfig
from researchledger.gold import Fact, candidates
from test_ingest_retrieve import make_repo


def test_fact_needs_every_number_and_half_the_distinctive_words():
    f = Fact.parse("FIVES test Dice 0.918")
    assert f.matches("The vessel segmenter reaches Dice 0.918 on the FIVES test split.")
    assert not f.matches("Dice 0.91 on FIVES test")  # number must match exactly
    assert not f.matches("0.918 seconds per step")  # number alone is not enough
    assert not Fact.parse("10.9").matches("value 110.95")  # digit-bounded


def test_archived_paths_are_flagged_and_never_proposed(tmp_path):
    repo, sha = make_repo(tmp_path, {
        "docs/current.md": "# Status\nThe vessel segmenter reaches FIVES test Dice 0.918.\n",
        "docs/archive/old.md": "# Old\nVessel segmenter: FIVES test Dice 0.918.\n",
        "docs/gold.md": "# Tracker\n| Asset | Numbers |\n|---|---|\n| Segmenter | FIVES test Dice 0.918 |\n",
    })
    cfg = CorpusConfig(name="t", source=str(repo), commit=sha, archived=("docs/archive/",))
    assert cfg.is_archived("docs/archive/old.md") and not cfg.is_archived("docs/current.md")
    qs = {
        "corpus": {"commit": sha[:7]},
        "files": {"G": "docs/gold.md"},
        "items": [{"id": "L1", "type": "lookup", "q": "How good is the segmenter?",
                   "must_include": ["FIVES test Dice 0.918"], "gold": [{"f": "G", "lines": [4, 4]}]}],
    }
    q = tmp_path / "q.yaml"
    q.write_text(yaml.safe_dump(qs))
    (item,) = candidates(cfg, q)
    # Not the archived copy, not the row already in gold. (A heading directly above a paragraph is part of its block.)
    assert [c["range"] for c in item["candidates"]] == ["docs/current.md:1-2"]
