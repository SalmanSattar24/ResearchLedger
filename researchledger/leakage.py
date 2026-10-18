"""Leakage scan: which files may be ingested, what fails ingestion, and what is redacted.

Rules (README, "Data boundary"):
- only text documents are ingested (ALLOWED_EXTENSIONS); everything else is skipped and counted;
- ingestion FAILS on anything that looks like a real secret, an embedded image, or a private person identifier;
- tokens in URL query parameters are REDACTED and each redaction is logged (file, line, parameter; never the value).

Findings never carry the matched value, so a failure report cannot itself leak the secret.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ALLOWED_EXTENSIONS = (".md", ".markdown", ".tex", ".ipynb")

REDACTED = "[REDACTED]"

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("service account key", re.compile(r'"private_key(_id)?"\s*:')),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("API secret key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b")),
    (
        "secret assignment",
        re.compile(
            r"^\s*(?:export\s+)?[A-Z][A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY)[A-Z0-9_]*\s*=\s*['\"]?[^\s'\"]{8,}",
            re.MULTILINE,
        ),
    ),
]
EMBEDDED_IMAGE = re.compile(r"data:image/[A-Za-z0-9.+\-]+;base64,")
EMAIL = re.compile(r"(?<![\w.+-])(?!git@)[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}\b")
URL_TOKEN = re.compile(
    r"([?&](?:access_?token|token|api_?key|key|sig|signature|auth|password|secret)=)([^&#\s)\]\"'>]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str


@dataclass(frozen=True)
class Redaction:
    path: str
    line: int
    param: str


class LeakageError(Exception):
    def __init__(self, findings: list[Finding]):
        self.findings = findings
        lines = "\n".join(f"  {f.path}:{f.line}: {f.kind}" for f in findings)
        super().__init__(f"ingestion refused, {len(findings)} leakage finding(s):\n{lines}")


Line = tuple[int, str]  # (line number in the original file, text of that line)


@dataclass
class ScanResult:
    lines: list[Line]
    redactions: list[Redaction] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


def is_allowed(path: str) -> bool:
    return path.lower().endswith(ALLOWED_EXTENSIONS)


def scan_lines(path: str, lines: list[Line]) -> ScanResult:
    """Redact URL tokens, then look for secrets, embedded images and email addresses in what remains.

    `lines` must be exactly what will be indexed (for a notebook: its markdown cells only), so outputs that are
    never ingested are never scanned either. Line numbers refer to the original file.
    """
    result = ScanResult(lines=[])
    for lineno, line in lines:
        for m in URL_TOKEN.finditer(line):
            result.redactions.append(Redaction(path, lineno, m.group(1).strip("?&=").lower()))
        line = URL_TOKEN.sub(lambda m: m.group(1) + REDACTED, line)
        result.lines.append((lineno, line))
        for kind, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                result.findings.append(Finding(path, lineno, kind))
        if EMBEDDED_IMAGE.search(line):
            result.findings.append(Finding(path, lineno, "embedded image"))
        if EMAIL.search(line):
            result.findings.append(Finding(path, lineno, "email address (person identifier)"))
    return result
