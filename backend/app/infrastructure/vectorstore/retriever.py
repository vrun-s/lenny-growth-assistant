"""Turns raw pgvector query rows into ranked, citation-ready SearchResults.
Pure data transformation — no DB session, no HTTP call — so it's testable
without Postgres or Ollama running.
"""

from collections.abc import Iterable, Sequence
from uuid import UUID

from app.domain.entities.document import Document
from app.domain.entities.search_result import SearchResult


def rank_results(rows: Iterable[Sequence]) -> list[SearchResult]:
    """Each row is (id, title, source, episode, speaker, timestamp_range,
    chunk, cosine_distance), pre-ordered nearest-first by the caller's query.
    Cosine distance is converted to a similarity score (higher = more similar).
    """
    results: list[SearchResult] = []
    for row_id, title, source, episode, speaker, timestamp_range, chunk, distance in rows:
        results.append(
            SearchResult(
                document=Document(
                    id=UUID(str(row_id)),
                    title=title,
                    source=source,
                    episode=episode,
                    chunk=chunk,
                    speaker=speaker,
                    timestamp_range=timestamp_range,
                ),
                score=1.0 - distance,
            )
        )
    return results
