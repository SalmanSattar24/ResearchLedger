import sqlite3
import subprocess

import pytest
import yaml

from researchledger.corpus import CorpusConfig
from researchledger.evaluate import evaluate_retrieval
from researchledger.ingest import ingest
from researchledger.leakage import LeakageError
from researchledger.retrieve import BM25Index, tokenize


def make_repo(tmp_path, files):
    repo = tmp_path / "repo"
    repo.mkdir()
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_bytes(text.encode() if isinstance(text, str) else text)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "c"], check=True)
    sha = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    return repo, sha


DOCS = {
    "docs/a.md": "# Alpha run\nWe used the Feistel shuffle.\n\n## Results\nMMLU was 65.3 after cooldown.\n",
    "docs/b.md": "# Beta run\nThe tokenizer was Llama 3.\n[r](https://wandb.ai/x?accessToken=zzzz)\n",
    "docs/fig.png": b"\x89PNG\r\n",
    "data/labels.csv": "id,label\n1,0\n",
    "untracked_later.md": "",
}


def test_ingest_builds_index_skips_non_text_and_logs_redactions(tmp_path):
    repo, sha = make_repo(tmp_path, DOCS)
    (repo / "uncommitted.md").write_text("must never be read")
    cfg = CorpusConfig(name="t", source=str(repo), commit=sha)
    report = ingest(cfg, tmp_path / "t.sqlite")
    assert report["files_ingested"] == {".md": 3}
    assert report["files_skipped_by_extension"] == {".csv": 1, ".png": 1}
    assert report["redactions"] == 1
    db = sqlite3.connect(tmp_path / "t.sqlite")
    texts = " ".join(t for (t,) in db.execute("SELECT text FROM chunks"))
    assert "zzzz" not in texts and "[REDACTED]" in texts and "must never be read" not in texts
    assert db.execute("SELECT path, line, param FROM redactions").fetchall() == [("docs/b.md", 3, "accesstoken")]


def test_ingest_refuses_a_secret_and_leaves_no_index(tmp_path):
    repo, sha = make_repo(tmp_path, {"a.md": "key " + "AKIA" + "ABCDEFGHIJKLMNOP" + "\n"})
    with pytest.raises(LeakageError) as e:
        ingest(CorpusConfig(name="t", source=str(repo), commit=sha), tmp_path / "t.sqlite")
    assert "a.md:1: AWS access key" in str(e.value)
    assert not (tmp_path / "t.sqlite").exists()


def test_include_and_exclude_prefixes(tmp_path):
    repo, sha = make_repo(tmp_path, DOCS)
    cfg = CorpusConfig(name="t", source=str(repo), commit=sha, include=("docs/",), exclude=("docs/b",))
    assert ingest(cfg, tmp_path / "t.sqlite")["files_ingested"] == {".md": 1}


def test_tokenize_keeps_compounds_and_parts():
    assert tokenize("QK-Norm at 1.7e-3") == ["qk-norm", "qk", "norm", "1.7e-3", "1", "7e", "3"]


def test_bm25_and_retrieval_eval(tmp_path):
    repo, sha = make_repo(tmp_path, DOCS)
    ingest(CorpusConfig(name="t", source=str(repo), commit=sha), tmp_path / "t.sqlite")
    top = BM25Index(tmp_path / "t.sqlite").search("which tokenizer?", k=1)[0]
    assert (top.path, top.start_line) == ("docs/b.md", 1)

    questions = {
        "corpus": {"commit": sha[:7]},
        "files": {"A": "docs/a.md", "B": "docs/b.md"},
        "items": [
            {"id": "L1", "type": "lookup", "q": "What was MMLU after cooldown?", "gold": [{"f": "A", "lines": [5, 5]}]},
            {"id": "L2", "type": "lookup", "q": "Which tokenizer?", "gold": [{"f": "B", "lines": [2, 2]}]},
            {"id": "X1", "type": "safety", "q": "capital of France?", "expect": "abstain"},
        ],
    }
    qpath = tmp_path / "q.yaml"
    qpath.write_text(yaml.safe_dump(questions))
    r = evaluate_retrieval(tmp_path / "t.sqlite", qpath)
    assert r["overall"]["n"] == 2 and r["overall"]["recall@1"] == "2/2 (100%)"
    assert r["overall"]["evidence@5"] == "0/0" or r["overall"]["evidence@5"] == "n/a"

    questions["corpus"]["commit"] = "0000000"
    qpath.write_text(yaml.safe_dump(questions))
    with pytest.raises(ValueError, match="pinned"):
        evaluate_retrieval(tmp_path / "t.sqlite", qpath)
