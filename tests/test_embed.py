from researchledger.corpus import CorpusConfig
from researchledger.embed import BM25Index, HybridIndex, embed_index, open_retriever
from researchledger.ingest import ingest
from researchledger.tools import LedgerIndex
from test_ingest_retrieve import DOCS, make_repo


def fake_embed(texts, task):
    """Vectors that put 'vocabulary' next to the tokenizer chunk, which shares no word with it."""
    return [[1.0, 0.0] if ("tokenizer" in t.lower() or "vocabulary" in t.lower()) else [0.0, 1.0] for t in texts]


def test_hybrid_finds_a_paraphrase_that_bm25_misses(tmp_path):
    repo, sha = make_repo(tmp_path, DOCS)
    path = tmp_path / "t.sqlite"
    ingest(CorpusConfig(name="t", source=str(repo), commit=sha), path)
    assert isinstance(open_retriever(path), BM25Index)  # auto: no vectors yet
    assert BM25Index(path).search("vocabulary", k=3) == []

    report = embed_index(path, fake_embed, model="fake")
    assert report["dim"] == 2 and report["chunks"] > 0
    hybrid = open_retriever(path, embed=fake_embed)
    assert isinstance(hybrid, HybridIndex)
    assert hybrid.search("vocabulary", k=1)[0].path == "docs/b.md"
    # the tools pick hybrid up the same way, and the index stays usable read-only
    assert LedgerIndex(path, embed=fake_embed).search("vocabulary", k=1)[0]["path"] == "docs/b.md"
