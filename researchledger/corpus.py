"""Corpus configuration and read-only access to a git repository at a pinned commit.

Files are listed and read from git objects (`git ls-tree`, `git cat-file`), never from a working tree, so the
source checkout is not touched and uncommitted files can never leak in.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

CACHE_DIR = Path(".cache/corpora")


@dataclass(frozen=True)
class CorpusConfig:
    name: str
    source: str  # local repository path or a git URL
    commit: str
    include: tuple[str, ...] = ()  # path prefixes; empty means the whole tree
    exclude: tuple[str, ...] = ()
    # Path prefixes the record itself marks as superseded (old plans, archived trackers). They stay in the index,
    # since history questions need them, but they are not where a current value should be cited from.
    archived: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: str | Path) -> CorpusConfig:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=raw["name"],
            source=str(raw["source"]),
            commit=str(raw["commit"]),
            include=tuple(raw.get("include", ())),
            exclude=tuple(raw.get("exclude", ())),
            archived=tuple(raw.get("archived", ())),
        )

    def is_archived(self, path: str) -> bool:
        return path.startswith(self.archived)


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def _is_url(source: str) -> bool:
    return source.startswith(("https://", "http://", "git@", "ssh://"))


class GitSource:
    """Read-only view of one commit of a repository."""

    def __init__(self, config: CorpusConfig, cache_dir: Path = CACHE_DIR):
        self.config = config
        self.repo = self._ensure_repo(config, cache_dir)
        self.commit = _git(self.repo, "rev-parse", f"{config.commit}^{{commit}}").decode().strip()

    @staticmethod
    def _ensure_repo(config: CorpusConfig, cache_dir: Path) -> Path:
        if not _is_url(config.source):
            return Path(config.source)
        repo = cache_dir / config.name
        if not (repo / ".git").exists() and not (repo / "HEAD").exists():
            repo.parent.mkdir(parents=True, exist_ok=True)
            # Blobless clone: trees are fetched now, file contents only when read.
            subprocess.run(
                ["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", config.source, str(repo)],
                check=True,
            )
        try:
            _git(repo, "cat-file", "-e", f"{config.commit}^{{commit}}")
        except subprocess.CalledProcessError:
            _git(repo, "fetch", "--quiet", "origin", config.commit)
        return repo

    def list_files(self) -> list[str]:
        out = _git(self.repo, "ls-tree", "-r", "-z", "--name-only", self.commit, "--", *self.config.include)
        paths = [p for p in out.decode("utf-8").split("\0") if p]
        return sorted(p for p in paths if not p.startswith(self.config.exclude))

    def read(self, path: str) -> bytes:
        return _git(self.repo, "cat-file", "blob", f"{self.commit}:{path}")
