"""Command line: ingest a corpus, search an index, evaluate retrieval."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .corpus import CorpusConfig
from .evaluate import evaluate_retrieval, write_results
from .ingest import ingest
from .leakage import LeakageError


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
    ps.add_argument("--retriever", choices=["auto", "bm25", "hybrid"], default="auto")

    pe = sub.add_parser("eval-retrieval", help="score retrieval against an evaluation set's gold ranges")
    pe.add_argument("--index", required=True)
    pe.add_argument("--questions", required=True)
    pe.add_argument("--out", required=True, help="results directory")
    pe.add_argument("--aggregate-only", action="store_true", help="omit per-item rows (for private corpora)")
    pe.add_argument("--retriever", choices=["bm25", "hybrid"], default="bm25")

    pm = sub.add_parser("embed", help="add Vertex AI embeddings to an index, for hybrid search (sends chunk text "
                                      "to Vertex AI: public corpora only)")
    pm.add_argument("--index", required=True)

    pq = sub.add_parser("eval-answers", help="run the agents on an evaluation set and grade every gate (calls Gemini)")
    pq.add_argument("--index", required=True)
    pq.add_argument("--questions", required=True)
    pq.add_argument("--out", required=True)
    pq.add_argument("--aggregate-only", action="store_true")
    pq.add_argument("--only", nargs="*", help="item ids to run (default: all)")
    pq.add_argument("--endpoint", help="grade a deployed service (its /ask) instead of running the agents here; "
                                       "an identity token is read from RL_ID_TOKEN")
    pq.add_argument("--fail-on-gate", action="store_true", help="exit 1 if any graded gate fails (for CI)")

    px = sub.add_parser("export-bigquery", help="load an index (and its vectors) into the BigQuery dataset")
    px.add_argument("--index", required=True)

    pa = sub.add_parser("ask", help="answer one question with the agents (calls Gemini on Vertex AI)")
    pa.add_argument("--index", required=True)
    pa.add_argument("question")

    ph = sub.add_parser("hand-check", help="write a seeded sample of judged items for a person to check the judge")
    ph.add_argument("--results", required=True, help="an answers-*.json results file")
    ph.add_argument("--out", required=True, help="output Markdown")
    ph.add_argument("--index", help="show each claim's cited lines from this index")
    ph.add_argument("--questions", help="show each item's question from this evaluation set")
    ph.add_argument("-n", type=int, default=10)

    args = p.parse_args(argv)
    if args.cmd == "ingest":
        try:
            report = ingest(CorpusConfig.load(args.corpus), args.index)
        except LeakageError as e:
            print(e, file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2))
    elif args.cmd == "search":
        from .embed import open_retriever

        for h in open_retriever(args.index, args.retriever).search(args.query, k=args.k):
            print(f"{h.score:6.2f}  {h.path}:{h.start_line}-{h.end_line}  [{h.heading}]")
    elif args.cmd == "eval-retrieval":
        results = evaluate_retrieval(args.index, args.questions, args.retriever)
        path = write_results(results, args.out, aggregate_only=args.aggregate_only)
        print(json.dumps({"overall": results["overall"], "by_type": results["by_type"]}, indent=2))
        print(f"written: {path}")
    elif args.cmd == "eval-answers":
        from .eval_answers import evaluate_answers

        path = evaluate_answers(args.index, args.questions, args.out, args.aggregate_only, args.only,
                                progress=lambda m: print(m, flush=True), endpoint=args.endpoint,
                                token=os.environ.get("RL_ID_TOKEN"))
        summary = json.loads(path.read_text(encoding="utf-8"))["summary"]
        for g in summary["gates"]:
            mark = {True: "PASS", False: "FAIL", None: "----"}[g["pass"]]
            print(f"{mark}  {g['gate']}: {g['result']} (required {g['required']})")
        print(f"written: {path}")
        if args.fail_on_gate and any(g["pass"] is False for g in summary["gates"]):
            return 1
    elif args.cmd == "hand-check":
        from .eval_answers import hand_check_sample

        print(f"written: {hand_check_sample(args.results, args.out, args.n, 0, args.index, args.questions)}")
    elif args.cmd == "export-bigquery":
        from .bigquery import export_index

        print(json.dumps(export_index(args.index), indent=2))
    elif args.cmd == "embed":
        from .embed import embed_index

        print(json.dumps(embed_index(args.index), indent=2))
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
