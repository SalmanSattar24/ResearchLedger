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

    pq = sub.add_parser("eval-answers", help="run the agents on an evaluation set and grade every gate (calls Gemini)")
    pq.add_argument("--index", required=True)
    pq.add_argument("--questions", required=True)
    pq.add_argument("--out", required=True)
    pq.add_argument("--aggregate-only", action="store_true")
    pq.add_argument("--only", nargs="*", help="item ids to run (default: all)")

    pa = sub.add_parser("ask", help="answer one question with the agents (calls Gemini on Vertex AI)")
    pa.add_argument("--index", required=True)
    pa.add_argument("question")

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
    elif args.cmd == "eval-answers":
        from .eval_answers import evaluate_answers

        path = evaluate_answers(args.index, args.questions, args.out, args.aggregate_only, args.only,
                                progress=lambda m: print(m, flush=True))
        summary = json.loads(path.read_text(encoding="utf-8"))["summary"]
        for g in summary["gates"]:
            mark = {True: "PASS", False: "FAIL", None: "----"}[g["pass"]]
            print(f"{mark}  {g['gate']}: {g['result']} (required {g['required']})")
        print(f"written: {path}")
    elif args.cmd == "ask":
        from .agents import ask
        from .tools import LedgerIndex

        r = ask(LedgerIndex(args.index), args.question)
        print(r.answer.model_dump_json(indent=2))
        print(json.dumps({"attempts": r.attempts, "problems": r.problems, "seconds": r.seconds, "usage": r.usage,
                          "trace": r.trace},
                         indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
