from __future__ import annotations

import os
import statistics

from rich import print
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.services.ingestion import create_document_from_text
from app.services.indexing import index_status, reindex_all
from app.services.qa import qa
from app.services.search import semantic_search

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")


def load_samples() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for name in sorted(os.listdir(SAMPLE_DIR)):
        if not (name.endswith(".txt") or name.endswith(".md")):
            continue
        path = os.path.join(SAMPLE_DIR, name)
        with open(path, "r", encoding="utf-8") as f:
            out.append((name, f.read()))
    return out


def main() -> None:
    init_db()
    db: Session = SessionLocal()

    samples = load_samples()
    if not samples:
        raise RuntimeError("No sample docs found in samples/")

    target_chunks = 1100

    # We want multiple chunks per doc.
    # Repeat the sample text so each doc is several thousand chars long.
    repeat_factor = 40  # adjust if needed; 40 usually yields multiple chunks/doc

    batch_docs = 20  # smaller batch to keep each reindex cycle reasonable
    created_total = 0

    while True:
        print("[cyan]Checking current chunk count...[/cyan]")
        status = index_status(db)
        print(f"[cyan]Current status[/cyan]: {status}")

        if status["chunks"] >= target_chunks:
            break

        start_i = created_total
        for i in range(start_i, start_i + batch_docs):
            name, txt = samples[i % len(samples)]

            long_body = (txt.strip() + "\n\n") * repeat_factor

            payload = f"""DocuSearch Sample Clone #{i}
Source: {name}
Repeat-Factor: {repeat_factor}

{long_body}

Clone-ID: {i}
"""
            create_document_from_text(
                db,
                filename=f"clone_{i}_{name}",
                content_type="text/plain",
                text=payload,
            )
            created_total += 1

        print(f"[bold]Added docs[/bold]: +{batch_docs} (total added this run: {created_total})")
        print("[cyan]Calling reindex_all()...[/cyan]")
        print("[bold]Reindexing all...[/bold]")
        reindex_all(db)
        print("[cyan]Reindex complete. Fetching status...[/cyan]")

        status = index_status(db)
        print(f"[green]Index status[/green]: {status}")

        # Safety valve: if something is still wrong, stop early with a clear error
        if created_total >= 250 and status["chunks"] < target_chunks:
            raise RuntimeError(
                f"Created {created_total} docs but still below target chunks. "
                f"Chunking may still be producing too few chunks/doc. "
                f"Try increasing repeat_factor."
            )

    # ---- Demo searches ----
    queries = [
        "deterministic chunking",
        "deduplicate documents sha256",
        "vector similarity search top k",
        "run requirements docker compose",
        "source citations in qa",
    ]

    times: list[float] = []
    for q in queries:
        r = semantic_search(db, q, top_k=5)
        times.append(r["retrieval_ms"])
        print(f"\n[bold]Search[/bold] q={q!r} retrieval_ms={r['retrieval_ms']:.2f}")
        print(r["results"][:2])

    print("\n[bold]Retrieval latency summary (ms)[/bold]")
    if times:
        times_sorted = sorted(times)
        p50 = statistics.median(times_sorted)
        p95 = times_sorted[max(0, int(round(0.95 * (len(times_sorted) - 1))))]
        print({"avg": statistics.mean(times_sorted), "p50": p50, "p95": p95})

    # ---- Demo Q&A ----
    questions = [
        "How does DocuSearch deduplicate documents?",
        "What does deterministic chunking mean here?",
        "What should the API do if the answer is not in the documents?",
    ]

    for q in questions:
        out = qa(db, q, top_k=5)
        print(f"\n[bold]QA[/bold] question={q!r} retrieval_ms={out['retrieval_ms']:.2f}")
        print(
            {
                "answer": out["answer"],
                "sources_count": len(out["sources"]),
                "sources_preview": out["sources"][:2],
            }
        )

    db.close()


if __name__ == "__main__":
    main()