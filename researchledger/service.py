"""HTTP service (Cloud Run): REST API and an MCP endpoint over one index.

    GET  /healthz         corpus, commit, retriever and SQL backend
    POST /search          {"query", "k"}: hybrid search, numbered lines and archived flags
    POST /ask             {"question", "trace"}: the agents and the verifier; answer, timing, tokens, cost
    /mcp/                 MCP (streamable HTTP): tools search, read_lines, ask

Access control is Cloud Run IAM (no unauthenticated invokers; see infra/), so the app itself has no login.
Configuration is environment only: RL_INDEX (SQLite index baked into the image), RL_SQL_BACKEND (sqlite or
bigquery), RL_RETRIEVER, RL_TRACE=1 to export OpenTelemetry spans to Cloud Trace.
"""

from __future__ import annotations

import contextlib
import logging
import os
import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .agents import _ask_async
from .llm import PROJECT, configure_vertex, genai_client
from .tools import LedgerIndex

log = logging.getLogger("researchledger")
INDEX = os.environ.get("RL_INDEX", "/app/index/marin.sqlite")


class State:
    index: LedgerIndex
    client = None


state = State()


def setup_tracing() -> None:
    """Export spans (ADK emits one per agent, model call and tool call) to Cloud Trace."""
    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id=PROJECT)))
    trace.set_tracer_provider(provider)


def build_mcp():
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

    # Cloud Run IAM authenticates every request before it reaches the app; the host check is for local servers.
    mcp = FastMCP("researchledger", stateless_http=True, json_response=True, streamable_http_path="/",
                  transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
                  instructions="Evidence-checked answers over a research record, with file and line citations.")

    @mcp.tool()
    def search(query: str, k: int = 6) -> list[dict]:
        """Hybrid search over the record. Each result: path, line range, heading, archived flag, numbered lines."""
        return state.index.search(query, k)

    @mcp.tool()
    def read_lines(path: str, start: int, end: int) -> dict:
        """Exact indexed lines start..end (at most 40) of a file, each prefixed with its line number."""
        return state.index.read_lines(path, start, end)

    @mcp.tool()
    async def ask(question: str) -> dict:
        """Answer a question (or check a claim: start it with 'Check:') with verified citations, or abstain."""
        return (await _answer(question, trace=False))

    return mcp


def create_app(index_path: str | None = None) -> FastAPI:
    """A fresh app (and MCP server: its session manager can run only once per instance)."""
    mcp = build_mcp()
    mcp_app = mcp.streamable_http_app()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_vertex()
        if os.environ.get("RL_TRACE") == "1":
            setup_tracing()
        state.index = LedgerIndex(index_path or INDEX)
        state.client = genai_client()
        t = time.perf_counter()
        state.index.search("warm up", 1)  # creates the embedding client and authenticates before any request
        log.warning("ready: %s@%s, warm-up %.1f s", state.index.name, state.index.commit[:12],
                    time.perf_counter() - t)
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="ResearchLedger", lifespan=lifespan)
    app.mount("/mcp", mcp_app)
    app.get("/healthz")(healthz)
    app.post("/search")(search)
    app.post("/ask")(ask)
    return app


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(6, ge=1, le=10)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    trace: bool = False


async def _answer(question: str, trace: bool) -> dict:
    r = await _ask_async(state.index, question, state.client)
    out = {"answer": r.answer.model_dump(), "attempts": r.attempts, "problems": r.problems, "seconds": r.seconds,
           "usage": r.usage, "corpus": state.index.name, "commit": state.index.commit}
    if trace:
        out["trace"] = r.trace
    return out


def healthz() -> dict:
    ix = state.index
    return {"corpus": ix.name, "commit": ix.commit, "retriever": type(ix.retriever).__name__,
            "sql_backend": ix.sql_backend}


def search(req: SearchRequest) -> list[dict]:
    return state.index.search(req.query, req.k)


async def ask(req: AskRequest) -> dict:
    return await _answer(req.question, req.trace)


app = create_app()
