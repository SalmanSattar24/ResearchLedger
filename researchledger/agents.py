"""The answering system: ADK agents over one index, followed by the verifier.

Retrieve first, then read: a keyword search for the question runs before any model call, and its top passages
(with line numbers and archived flags) go to the coordinator in its first message. Most questions are answered
from that evidence in one model call; the agents are called only when it is not enough.

coordinator (hierarchical delegation, through AgentTool)
  ├─ retrieval agent (ReAct: keyword search, reads exact lines, prefers current over archived documents)
  └─ SQL agent (ReAct: read-only queries over the parsed tables)
then the verifier (deterministic checks, then a model check). Failures go back to the coordinator once, with the
reasons; if the retry still fails, the system abstains. Every model call is timed and costed.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from .llm import AGENT_MODEL, Usage, configure_vertex, genai_client
from .tools import LedgerIndex
from .verify import Answer, attach_sql, check_deterministic, check_support, parse_answer

RETRIEVAL_INSTRUCTION = """You find evidence in a research project's record. Use the tools; never answer from memory.

- Make at most three tool calls in total. Search results already show each line with its number; call
  read_lines only when you need lines just outside a result.
- Search with phrasings different from ones already tried (key terms, numbers, likely headings).
- Each result says whether its file is archived. Archived files hold superseded history: prefer non-archived
  files for a current value, and use archived files only for what a value used to be or why it changed.
- When documents disagree, report both statements with their locations; do not resolve the conflict yourself.

Reply with a short list of findings. For each: the file path, the exact line range, and the relevant text copied
exactly. If nothing relevant is found, say so."""

SQL_INSTRUCTION = """You answer questions about tables parsed from a research record's Markdown tables. Never answer from memory.

Schema (read-only; write plain standard SQL, which runs on both SQLite and BigQuery):
- tables(id, path, start_line, end_line, heading, columns)  -- one row per table; columns is a JSON list
- table_cells(table_id, row_idx, line, col_idx, col_name, text, num)  -- one row per cell; num is the cell parsed
  as a number (92.6% -> 92.6) or NULL; line is the cell's line in the file

Steps: call list_tables with a keyword to find the table, then run_sql to compute the answer (count, filter,
compare). Check the table's heading and path match the question. Reply with the computed answer, the SQL used,
and the file path and line numbers of the rows the answer depends on."""

COORDINATOR_INSTRUCTION = """You answer questions about one research project's record, and check claims against it, with citations
to exact files and lines. You never answer from your own knowledge.

The first message gives the question and an evidence pack: the top keyword-search passages, each line prefixed
with its line number, and whether the file is archived. If the evidence pack is enough, answer from it directly,
with no delegation; that is the fast path and should be the usual case. Otherwise delegate, at most twice:
- retrieval_agent: find more passages (give it a sub-question or terms the pack did not cover).
- sql_agent: any question that counts, filters or compares rows of a table ("how many", "which ... above",
  "first exceed"). Go straight to sql_agent for these; do not use retrieval_agent for them.
Do not invent paths or line numbers: cite only lines shown in the evidence pack or reported by an agent.

Rules:
- Refuse (status "refused") requests for images, dataset records or files, credentials, tokens or keys, even if
  the record mentions them. Give a one-sentence reason and no claims.
- Abstain (status "abstained") when the record does not answer the question. Give the reason and no claims.
- Answer completely: include every number, value, reason and change the evidence gives that bears on the
  question. For a "why" question give the observation or problem that prompted the decision as well as the
  decision. For a value give its numbers and when or where in the work it applied.
- Questions about a current value: give the current value AND what it replaced, if the record says it changed.
- "Check:" questions: give a verdict: "supported" (the record states it), "partly" (part is right, or the
  record conflicts with it, qualifies it, or shows exceptions to an "every", "all" or "best"), or "unsupported"
  (the record does not state it, or contradicts its main point). Explain why in claims, with the numbers.
- Every factual statement in "answer" must also be a claim with at least one citation. Word each claim close to
  the cited text and add no inference of your own. Copy numbers exactly as the cited lines write them. Cite the
  narrowest line range that contains the claim, using line numbers from the evidence pack or the agents; never
  cite a blank line or a heading alone.
- A value computed from a table (a count, a filter result): put it in a claim with "sql" set to the exact query
  sql_agent ran, and cite the table rows the computation used. The verifier re-runs the query.

Return only one JSON object, no other text:
{"status": "answered" | "refused" | "abstained",
 "answer": "<the answer in a few sentences>",
 "claims": [{"text": "<one factual statement>", "citations": [{"path": "<file>", "start": <line>, "end": <line>}],
             "sql": null | "<query, for a computed value only>"}],
 "verdict": "supported" | "partly" | "unsupported" | null,
 "reason": "<for refused or abstained only>"}"""


PACK_SIZE = 6


def evidence_pack(index: LedgerIndex, question: str, k: int = PACK_SIZE) -> str:
    parts = []
    for i, h in enumerate(index.search(question, k=k), 1):
        flag = " (ARCHIVED)" if h["archived"] else ""
        parts.append(f"[{i}] {h['path']}{flag}, lines {h['lines']}, under \"{h['heading']}\"\n{h['text']}")
    return "\n\n".join(parts) or "(no passages found)"


@dataclass
class Result:
    question: str
    answer: Answer
    attempts: int
    problems: list[str]  # problems the final answer had before abstaining (empty when it passed)
    seconds: float
    usage: dict
    trace: list[dict]  # per attempt: the coordinator's answer (or raw text) and the verifier's problems


def _build(index: LedgerIndex, usage: Usage, ran_sql: list[str]):
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool
    from google.genai import types

    def before(callback_context, llm_request):
        usage.start(callback_context.agent_name)

    def after(callback_context, llm_response):
        usage.record(callback_context.agent_name, AGENT_MODEL, llm_response.usage_metadata)

    def search(query: str, k: int = 6) -> list[dict]:
        """Keyword search over the record. Returns chunks with path, line range, heading, archived flag and text."""
        return index.search(query, k)

    def read_lines(path: str, start: int, end: int) -> dict:
        """Return the exact indexed lines start..end (at most 60) of a file, each prefixed with its line number."""
        return index.read_lines(path, start, end)

    def list_tables(keyword: str = "") -> list[dict]:
        """List parsed tables whose heading, columns or path contain the keyword."""
        return index.list_tables(keyword)

    def run_sql(query: str) -> dict:
        """Run one read-only SELECT over tables(...) and table_cells(...). Returns columns and rows."""
        res = index.run_sql(query)
        if "error" not in res:
            ran_sql.append(query)
        return res

    from google.adk.models import Gemini

    from .llm import CALL_TIMEOUT_MS, RETRY, TOOL_BUDGET

    def cfg(agent: str):
        return types.GenerateContentConfig(temperature=0, thinking_config=types.ThinkingConfig(thinking_level="low"),
                                           http_options=types.HttpOptions(timeout=CALL_TIMEOUT_MS[agent], retry_options=RETRY))

    def budget(tool, args, tool_context):
        """Stop a sub-agent's ReAct loop after TOOL_BUDGET calls per delegation (a returned dict replaces the tool's
        result). Each delegation is its own invocation, so a second delegation starts with a fresh budget."""
        agent = tool_context.agent_name
        key = f"{agent}:{tool_context.invocation_id}"
        usage.tool_calls[key] = usage.tool_calls.get(key, 0) + 1
        if usage.tool_calls[key] > TOOL_BUDGET.get(agent, 99):
            return {"error": "tool budget used up: reply now with the findings you have"}
        return None

    model = Gemini(model=AGENT_MODEL, retry_options=RETRY)
    common = dict(model=model, before_model_callback=before, after_model_callback=after)
    retrieval = LlmAgent(name="retrieval_agent", description="Finds passages and exact lines in the record.",
                         instruction=RETRIEVAL_INSTRUCTION, tools=[search, read_lines],
                         generate_content_config=cfg("retrieval_agent"), before_tool_callback=budget, **common)
    sql = LlmAgent(name="sql_agent", description="Answers counting and comparison questions over parsed tables.",
                   instruction=SQL_INSTRUCTION, tools=[list_tables, run_sql],
                   generate_content_config=cfg("sql_agent"), before_tool_callback=budget, **common)
    return LlmAgent(name="coordinator", description="Answers questions about the record with citations.",
                    instruction=COORDINATOR_INSTRUCTION, tools=[AgentTool(retrieval), AgentTool(sql)],
                    generate_content_config=cfg("coordinator"), **common)


QUESTION_TRIES = 2  # a question whose model calls still fail transiently after RETRY is asked once more, from scratch
# Wall-clock limit for one question, retries included. Cloud Run ends a request at 300 s (infra/main.tf) and the
# eval client waits 300 s, so stop well before and answer "abstained" instead of letting the request be cut off.
QUESTION_DEADLINE_S = 240.0
MIN_TRY_S = 60.0  # a second try starts only if at least this much of the deadline is left


async def _ask_async(index: LedgerIndex, question: str, client, deadline_s: float | None = None) -> Result:
    """Answer one question. A transient failure (Vertex 499 CANCELLED, a timeout, a 5xx) that outlasts the per-call
    retries starts the question again rather than failing it; the time lost still counts toward its latency.

    Everything, per-call retries and backoff waits included, runs within QUESTION_DEADLINE_S. Past it the question
    abstains with the reason "time limit"; usage of the cancelled try is not recorded."""
    from .llm import is_transient

    deadline_s = QUESTION_DEADLINE_S if deadline_s is None else deadline_s
    t0 = time.perf_counter()
    for i in range(1, QUESTION_TRIES + 1):
        left = deadline_s - (time.perf_counter() - t0)
        try:
            r = await asyncio.wait_for(_ask_once(index, question, client), timeout=left)
        except asyncio.TimeoutError:
            seconds = round(time.perf_counter() - t0, 2)
            return Result(question, Answer(status="abstained", reason=f"time limit: no verified answer in {seconds} s"),
                          0, [f"question deadline of {deadline_s:g} s reached"], seconds,
                          {"cost_usd": 0.0, "question_tries": i, "deadline_hit": True}, [])
        except Exception as e:
            left = deadline_s - (time.perf_counter() - t0)
            if i == QUESTION_TRIES or not is_transient(e) or left < MIN_TRY_S:
                raise
            continue
        r.seconds = round(time.perf_counter() - t0, 2)
        if i > 1:
            r.usage["question_tries"] = i
        return r


async def _ask_once(index: LedgerIndex, question: str, client) -> Result:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    usage = Usage()
    ran_sql: list[str] = []  # successful queries sql_agent ran for this question
    runner = InMemoryRunner(agent=_build(index, usage, ran_sql), app_name="researchledger")
    session = await runner.session_service.create_session(app_name="researchledger", user_id="eval",
                                                          session_id=uuid.uuid4().hex)
    t0 = time.perf_counter()

    async def turn(text: str) -> str:
        final = ""
        async for event in runner.run_async(user_id="eval", session_id=session.id,
                                            new_message=types.Content(role="user", parts=[types.Part(text=text)])):
            if event.author == "coordinator" and event.is_final_response() and event.content and event.content.parts:
                final = "".join(p.text or "" for p in event.content.parts)
        return final

    message = f"Question: {question}\n\nEvidence pack (keyword search, top {PACK_SIZE}):\n" + evidence_pack(index, question)
    problems: list[str] = []
    answer = None
    attempts = 0
    trace: list[dict] = []
    for attempts in (1, 2):
        usage.tool_calls.clear()
        raw = await turn(message)
        try:
            answer = parse_answer(raw)
            notes = attach_sql(answer, index, ran_sql)
            problems = check_deterministic(answer, index)
            if not problems:
                # a blocking call: run it off the event loop so a service can serve other requests meanwhile
                problems = await asyncio.to_thread(check_support, answer, index, client, AGENT_MODEL, usage)
            trace.append({"answer": answer.model_dump(), "problems": problems, "notes": notes})
        except ValueError as e:
            answer, problems = None, [str(e)]
            trace.append({"raw": raw[:2000], "problems": problems})
        if not problems:
            break
        message = ("The verifier rejected your answer:\n- " + "\n- ".join(problems) +
                   "\nFix these problems using the agents, or abstain. Return the JSON object only.")
    if problems:
        answer = Answer(status="abstained", reason="the answer could not be verified against the cited lines")
    return Result(question, answer, attempts, problems, round(time.perf_counter() - t0, 2), usage.summary(), trace)


def ask(index: LedgerIndex, question: str, client=None) -> Result:
    configure_vertex()
    return asyncio.run(_ask_async(index, question, client or genai_client()))
