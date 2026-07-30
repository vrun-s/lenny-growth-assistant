from uuid import uuid4

from app.infrastructure.vectorstore.retriever import rank_results


def test_rank_results_converts_distance_to_similarity_score():
    doc_id = uuid4()
    rows = [(doc_id, "Title", "source.md", "Ep 1", "Lenny", "00:00:01", "chunk text", 0.2)]

    results = rank_results(rows)

    assert len(results) == 1
    assert results[0].score == 0.8
    assert results[0].document.id == doc_id
    assert results[0].document.chunk == "chunk text"
    assert results[0].document.speaker == "Lenny"


def test_rank_results_preserves_row_order():
    rows = [
        (uuid4(), "A", "a.md", "Ep 1", None, None, "first", 0.1),
        (uuid4(), "B", "b.md", "Ep 2", None, None, "second", 0.4),
    ]

    results = rank_results(rows)

    assert [r.document.chunk for r in results] == ["first", "second"]


def test_rank_results_empty_input_returns_empty_list():
    assert rank_results([]) == []
