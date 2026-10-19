import pytest

pytest.importorskip("fastapi")
pytest.importorskip("mcp")

from fastapi.testclient import TestClient  # noqa: E402

from researchledger.corpus import CorpusConfig  # noqa: E402
from researchledger.ingest import ingest  # noqa: E402
from test_ingest_retrieve import DOCS, make_repo  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    repo, sha = make_repo(tmp_path, DOCS)
    ingest(CorpusConfig(name="t", source=str(repo), commit=sha), tmp_path / "t.sqlite")
    from researchledger import service

    monkeypatch.setattr(service, "genai_client", lambda: None)  # no network: /ask is not exercised here
    with TestClient(service.create_app(str(tmp_path / "t.sqlite"))) as c:
        yield c, sha


def test_health_and_search(client):
    c, sha = client
    h = c.get("/health").json()
    assert h == {"corpus": "t", "commit": sha, "retriever": "BM25Index", "sql_backend": "sqlite"}
    hits = c.post("/search", json={"query": "which tokenizer", "k": 1}).json()
    assert hits[0]["path"] == "docs/b.md" and hits[0]["text"].startswith("1: # Beta run")
    assert c.post("/search", json={"query": "", "k": 1}).status_code == 422


def test_mcp_lists_and_calls_tools(client):
    c, _ = client
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
    assert c.post("/mcp/", json=init, headers=headers).status_code == 200
    tools = c.post("/mcp/", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=headers).json()
    assert {t["name"] for t in tools["result"]["tools"]} == {"search", "read_lines", "ask"}
    call = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "read_lines", "arguments": {"path": "docs/b.md", "start": 2, "end": 2}}}
    out = c.post("/mcp/", json=call, headers=headers).json()
    assert "The tokenizer was Llama 3." in out["result"]["content"][0]["text"]
