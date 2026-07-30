"""CLI entrypoint for the ingestion pipeline. Zero business logic — calls
straight into infrastructure/ingestion/ and application/use_cases/, per
ARCHITECTURE.md §2.1 ("scripts/ ... Must not contain core business algorithms
or raw parser logic").

Usage:
    python scripts/run_ingestion.py path/to/transcript.md [--episode "Episode 12"]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.application.use_cases.ingest_documents import IngestDocumentsUseCase
from app.infrastructure.ingestion.loader import load_transcript
from app.infrastructure.vectorstore.pgvector_store import PgVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a Markdown transcript into pgvector.")
    parser.add_argument("path", type=Path, help="Path to a Markdown transcript file")
    parser.add_argument("--episode", default=None, help="Episode label (defaults to the parsed title)")
    parser.add_argument("--source", default=None, help="Source URL (defaults to the file path)")
    args = parser.parse_args()

    markdown = args.path.read_text(encoding="utf-8")
    documents = load_transcript(
        markdown, episode=args.episode, default_source=args.source or str(args.path)
    )

    use_case = IngestDocumentsUseCase(PgVectorStore())
    ingested = use_case.execute(documents)

    print(f"Ingested {ingested} chunk(s) from {args.path}")


if __name__ == "__main__":
    main()
