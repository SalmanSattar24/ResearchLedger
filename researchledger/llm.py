"""Model configuration, Vertex AI access and cost accounting.

Models run on Vertex AI in the project's own GCP project. The project id is taken from RL_GCP_PROJECT (default
researchledger-2026). The user's application-default credentials may carry another project as quota project, so
the quota project is set explicitly for this process and never changed globally.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

PROJECT = os.environ.get("RL_GCP_PROJECT", "researchledger-2026")
LOCATION = os.environ.get("RL_GCP_LOCATION", "global")

AGENT_MODEL = os.environ.get("RL_AGENT_MODEL", "gemini-3.7-flash")
# The judge is a different model family from the agents, so answers are not graded by their own model.
JUDGE_MODEL = os.environ.get("RL_JUDGE_MODEL", "gemini-2.5-pro")

# USD per 1M tokens (input, output), Vertex AI standard tier, global endpoint, checked 17 Oct 2026 at
# https://cloud.google.com/vertex-ai/generative-ai/pricing . 3.x Flash rates are introductory until 31 Dec 2026.
# Thinking tokens are billed as output.
PRICES = {
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-2.5-pro": (1.25, 10.0),
}


def _retry():
    from google.genai import types

    # Shared Gemini capacity returns 429 under bursts, and 504 when a request passes its timeout; back off and retry. Waits count toward measured latency.
    return types.HttpRetryOptions(attempts=6, initial_delay=2.0, max_delay=60.0, exp_base=2.0, jitter=1.0,
                                  http_status_codes=[429, 500, 503, 504])


RETRY = _retry()

# Per-request timeout. Most calls take 2-6 s, but on shared capacity a call occasionally hangs for 25-50 s; a timeout
# is retried (with RETRY), which is faster than waiting. The coordinator writes the longest output, so it gets more.
CALL_TIMEOUT_MS = {"coordinator": 25_000, "retrieval_agent": 15_000, "sql_agent": 15_000, "verifier": 15_000}
# Tool calls allowed per sub-agent per question; past that a tool returns an error asking for the findings so far.
TOOL_BUDGET = {"retrieval_agent": 3, "sql_agent": 4}


def _is_user_login(creds) -> bool:
    from google.oauth2 import credentials as user_credentials

    return isinstance(creds, user_credentials.Credentials)


def credentials():
    """Application-default credentials for PROJECT.

    A person's login (gcloud auth application-default login) may carry another project as quota project, so it is
    billed to PROJECT explicitly. Service accounts (Cloud Run) and federated identities (GitHub Actions) already
    bill to their own project, and a quota project on them would require the extra Service Usage Consumer role."""
    import google.auth

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return creds.with_quota_project(PROJECT) if _is_user_login(creds) else creds


def configure_vertex() -> None:
    """Point google-genai (used by ADK) at Vertex AI in PROJECT, for this process only."""
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT
    os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION
    if _is_user_login(credentials()):
        os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = PROJECT
    else:
        os.environ.pop("GOOGLE_CLOUD_QUOTA_PROJECT", None)


def genai_client():
    from google import genai

    configure_vertex()
    creds = credentials()
    return genai.Client(vertexai=True, project=PROJECT, location=LOCATION, credentials=creds,
                        http_options=genai.types.HttpOptions(retry_options=RETRY))


@dataclass
class ModelCall:
    agent: str
    model: str
    seconds: float
    input_tokens: int
    output_tokens: int  # candidates + thinking

    @property
    def cost(self) -> float:
        p_in, p_out = PRICES.get(self.model, (0.0, 0.0))
        return (self.input_tokens * p_in + self.output_tokens * p_out) / 1e6


@dataclass
class Usage:
    """Every model call made while answering one question, with per-step latency and cost."""

    calls: list[ModelCall] = field(default_factory=list)
    _started: dict[str, float] = field(default_factory=dict)
    tool_calls: dict[str, int] = field(default_factory=dict)  # per agent, in the current attempt (TOOL_BUDGET)

    def start(self, agent: str) -> None:
        self._started[agent] = time.perf_counter()

    def record(self, agent: str, model: str, usage_metadata) -> None:
        seconds = time.perf_counter() - self._started.pop(agent, time.perf_counter())
        u = usage_metadata
        inp = (getattr(u, "prompt_token_count", 0) or 0) if u else 0
        out = ((getattr(u, "candidates_token_count", 0) or 0) + (getattr(u, "thoughts_token_count", 0) or 0)) if u else 0
        self.calls.append(ModelCall(agent, model, seconds, inp, out))

    def summary(self) -> dict:
        by_agent: dict[str, dict] = {}
        for c in self.calls:
            a = by_agent.setdefault(c.agent, {"calls": 0, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0})
            a["calls"] += 1
            a["seconds"] = round(a["seconds"] + c.seconds, 2)
            a["input_tokens"] += c.input_tokens
            a["output_tokens"] += c.output_tokens
        tin = sum(c.input_tokens for c in self.calls)
        tout = sum(c.output_tokens for c in self.calls)
        secs = sum(c.seconds for c in self.calls)
        return {
            "model_calls": len(self.calls),
            "input_tokens": tin,
            "output_tokens": tout,
            "output_tokens_per_second": round(tout / secs, 1) if secs else None,
            "cost_usd": round(sum(c.cost for c in self.calls), 5),
            "by_agent": by_agent,
        }
