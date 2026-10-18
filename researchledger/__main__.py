"""Command line: ingest a corpus, search an index, evaluate retrieval."""

from __future__ import annotations

import argparse
import json
import sys

from .corpus import CorpusConfig
from .evaluate import evaluate_retrieval, write_results
from .ingest import ingest
from .leakage import LeakageError
from .retrieve import BM25Index


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="researchledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="build an index from a corpus config")
    pi.add_argument("--corpus", required=True, help="corpus YAML (name, source, commit, include, exclude)")
    pi.add_argument("--index", required=True, help="output SQLite index")

    ps = sub.add_parser("search", help="keyword search an index")
    ps.add_argument("--index", required=True)
    ps.add_argument("query")
    ps.add_argument("-k", type=int, default=5)

    pe = sub.add_parser("eval-retrieval", help="score retrieval against an evaluation set's gold ranges")
    pe.add_argument("--index", required=True)
    pe.add_argument("--questions", required=True)
    pe.add_argument("--out", required=True, help="results directory")
    pe.add_argument("--aggregate-only", action="store_true", help="omit per-item rows (for private corpora)")

    args = p.parse_args(argv)
    if args.cmd == "ingest":
        try:
            report = ingest(CorpusConfig.load(args.corpus), args.index)
        except LeakageError as e:
            print(e, file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2))
    elif args.cmd == "search":
        for h in BM25Index(args.index).search(args.query, k=args.k):
            print(f"{h.score:6.2f}  {h.path}:{h.start_line}-{h.end_line}  [{h.heading}]")
    elif args.cmd == "eval-retrieval":
        results = evaluate_retrieval(args.index, args.questions)
        path = write_results(results, args.out, aggregate_only=args.aggregate_only)
        print(json.dumps({"overall": results["overall"], "by_type": results["by_type"]}, indent=2))
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
