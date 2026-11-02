"""Opt-in Gemini Developer API adapter. No Vertex, tools, paid fallback or retries.

Limits constrain usage, not the provider's billing status. An operator must
confirm that the supplied key belongs to a project without active paid billing.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = "gemini-3.5-flash-lite"


class DemoUnavailable(Exception):
    """Safe public error; never include provider response bodies or credentials."""


class CallBudget:
    """Atomic, restart-persistent global allowance; failed calls stay charged.

    Reserve both generation and verification together before either network call.
    No client-controlled key/session can bypass this global quota.
    """
    def __init__(self, path: str | Path, daily: int = 20, minute: int = 4, clock=time.time):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.daily = max(0, min(int(daily), 20))
        self.minute = max(0, min(int(minute), 4))
        self.clock = clock
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS reservations (at REAL NOT NULL, calls INTEGER NOT NULL)")

    def reserve(self, calls: int = 2):
        now = self.clock()
        day = int(now // 86400) * 86400
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            used = db.execute("SELECT coalesce(sum(calls),0) FROM reservations WHERE at >= ?", (day,)).fetchone()[0]
            recent = db.execute("SELECT coalesce(sum(calls),0) FROM reservations WHERE at > ?", (now - 60,)).fetchone()[0]
            if calls <= 0 or used + calls > self.daily or recent + calls > self.minute:
                raise DemoUnavailable("The demo's model-call allowance is exhausted. Retrieval remains available.")
            db.execute("INSERT INTO reservations VALUES (?,?)", (now, calls))


class GeminiFreeProvider:
    def __init__(self, budget: CallBudget, opener=urlopen):
        self.budget = budget
        self.opener = opener

    @staticmethod
    def enabled() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY")) and os.environ.get("RL_DEMO_FREE_TIER_CONFIRMED") == "1"

    def reserve(self):
        if not self.enabled():
            raise DemoUnavailable("Generated answers are disabled until a free-tier key and operator confirmation are configured.")
        self.budget.reserve(2)

    def generate(self, system: str, content: str) -> dict:
        if not self.enabled():
            raise DemoUnavailable("Generated answers are disabled.")
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": content}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1536, "responseMimeType": "application/json"},
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
            data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        )
        try:
            with self.opener(request, timeout=30) as response:
                raw = response.read(200_001)
            if len(raw) > 200_000:
                raise ValueError("oversize")
            result = json.loads(raw)
            candidate = result["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise ValueError("incomplete or blocked")
            text = "".join(p.get("text", "") for p in candidate["content"]["parts"] if not p.get("thought"))
            result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError("object required")
            return result
        except HTTPError as e:
            # HTTPError's string/URL/body can contain secret or untrusted data.
            raise DemoUnavailable(f"Model request failed (HTTP {e.code}); no retry or fallback was attempted.") from None
        except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
            raise DemoUnavailable("The model returned no complete usable response; no retry or fallback was attempted.") from None
