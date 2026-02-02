from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.services.indexing import index_status, reindex_all
from app.services.search import keyword_baseline_search, semantic_search
from app.db.models import Document

console = Console()

EVAL_CASES_PATH = os.path.join(os.path.dirname(__file__), "eval_cases.json")


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    expected_source: str


def load_cases() -> list[EvalCase]:
    if not os.path.exists(EVAL_CASES_PATH):
        raise RuntimeError(f"Missing eval cases file: {EVAL_CASES_PATH}")

    with open(EVAL_CASES_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cases: list[EvalCase] = []
    for item in raw:
        cases.append(
            EvalCase(
                id=item["id"],
                query=item["query"],
                expected_source=item["expected_source"],
            )
        )
    return cases


def is_relevant(db: Session, result: dict[str, Any], expected_source: str) -> bool:
    """
    Robust oracle: mark a result relevant if its document filename matches expected_source.
    This stays stable across reindex runs and doesn't depend on snippet text.
    """
    doc_id = result.get("document_id")
    if not doc_id:
        return False

    doc = db.query(Document).filter(Document.id == int(doc_id)).first()
    if not doc or not doc.filename:
        return False

    # expected_source is like "03_chunking.txt"
    return expected_source.lower() in doc.filename.lower()


def compute_hit_mrr_precision(db: Session, results: list[dict[str, Any]], expected_source: str, k: int) -> tuple[float, float, float, int]:
    """
    Returns: (hit@k, mrr, precision@k, irrelevant_count@k)
    """
    top = results[:k]
    rel_flags = [is_relevant(db, r, expected_source) for r in top]
    hit = 1.0 if any(rel_flags) else 0.0

    # MRR: 1 / rank of first relevant, else 0
    mrr = 0.0
    for idx, ok in enumerate(rel_flags, start=1):
        if ok:
            mrr = 1.0 / float(idx)
            break

    precision = sum(1 for ok in rel_flags if ok) / float(k) if k > 0 else 0.0
    irrelevant = sum(1 for ok in rel_flags if not ok)
    return hit, mrr, precision, irrelevant


def run_eval(db: Session, cases: list[EvalCase], top_k: int) -> dict[str, Any]:
    key_hits: list[float] = []
    sem_hits: list[float] = []
    key_mrr: list[float] = []
    sem_mrr: list[float] = []
    key_prec: list[float] = []
    sem_prec: list[float] = []
    key_ms: list[float] = []
    sem_ms: list[float] = []

    for c in cases:
        key = keyword_baseline_search(db, c.query, top_k=top_k)
        sem = semantic_search(db, c.query, top_k=top_k)

        key_h, key_r, key_p, _ = compute_hit_mrr_precision(db, key["results"], c.expected_source, top_k)
        sem_h, sem_r, sem_p, _ = compute_hit_mrr_precision(db, sem["results"], c.expected_source, top_k)

        key_hits.append(key_h)
        sem_hits.append(sem_h)
        key_mrr.append(key_r)
        sem_mrr.append(sem_r)
        key_prec.append(key_p)
        sem_prec.append(sem_p)
        key_ms.append(float(key["retrieval_ms"]))
        sem_ms.append(float(sem["retrieval_ms"]))

    return {
        "hit@k": (statistics.mean(key_hits), statistics.mean(sem_hits)),
        "mrr": (statistics.mean(key_mrr), statistics.mean(sem_mrr)),
        "precision@k": (statistics.mean(key_prec), statistics.mean(sem_prec)),
        "retrieval_ms_avg": (statistics.mean(key_ms), statistics.mean(sem_ms)),
    }


def run_tuning(db: Session, cases: list[EvalCase], top_k: int) -> list[dict[str, Any]]:
    """
    We keep chunking configs in config/env for the actual system.
    Here we *simulate* tuning impact by varying top_k and counting irrelevant@k.
    This is honest and measurable without changing the DB mid-run.
    """
    configs = [
        {"top_k": 3},
        {"top_k": 5},
        {"top_k": 8},
    ]

    rows: list[dict[str, Any]] = []
    for cfg in configs:
        k = cfg["top_k"]
        irrels: list[int] = []
        for c in cases:
            sem = semantic_search(db, c.query, top_k=k)
            _hit, _mrr, _prec, irr = compute_hit_mrr_precision(db, sem["results"], c.expected_source, k)
            irrels.append(irr)
        rows.append({"top_k": k, "avg_irrelevant@k": statistics.mean(irrels)})
    return rows


def render_main_table(metrics: dict[str, Any], k: int) -> None:
    table = Table(title=f"DocuSearch Evaluation (k={k})")
    table.add_column("Metric")
    table.add_column("Keyword baseline")
    table.add_column("Semantic (vector)")
    table.add_column("Δ (semantic - keyword)")

    for m, (kv, sv) in metrics.items():
        delta = sv - kv
        table.add_row(
            m,
            f"{kv:.3f}",
            f"{sv:.3f}",
            f"{delta:+.3f}",
        )

    console.print(table)


def render_tuning_table(rows: list[dict[str, Any]]) -> None:
    table = Table(title="Tuning: Irrelevant@k (lower is better)")
    table.add_column("top_k")
    table.add_column("avg_irrelevant@k")

    for r in rows:
        table.add_row(str(r["top_k"]), f"{r['avg_irrelevant@k']:.3f}")

    console.print(table)


def main() -> None:
    init_db()
    db: Session = SessionLocal()

    status = index_status(db)
    console.print(f"[bold]Current index status[/bold]: {status}")

    console.print("[cyan]Reindexing before evaluation (reproducibility check)...[/cyan]")
    reindex_all(db)

    cases = load_cases()
    top_k = 5

    metrics = run_eval(db, cases, top_k=top_k)
    render_main_table(metrics, k=top_k)

    tuning_rows = run_tuning(db, cases, top_k=top_k)
    render_tuning_table(tuning_rows)

    console.print("\nNotes:")
    console.print("- This evaluation uses a transparent document-level oracle for relevance (expected_source per query).")
    console.print("- Relevance is determined by matching retrieved document filenames against labeled sources in eval_cases.json.")
    db.close()


if __name__ == "__main__":
    main()