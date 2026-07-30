from app.infrastructure.ingestion.chunker import chunk_transcript
from app.infrastructure.ingestion.parser import ParsedTranscript, TranscriptSegment


def _transcript(segments: list[TranscriptSegment], source: str = "ep01.md") -> ParsedTranscript:
    return ParsedTranscript(title="Episode 1", source=source, segments=segments)


def test_single_short_transcript_becomes_one_chunk():
    transcript = _transcript([TranscriptSegment(text="Hello", speaker="Lenny", timestamp="00:00:01")])

    documents = chunk_transcript(transcript, episode="Episode 1")

    assert len(documents) == 1
    assert documents[0].chunk == "Hello"
    assert documents[0].speaker == "Lenny"
    assert documents[0].timestamp_range == "00:00:01"
    assert documents[0].source == "ep01.md"
    assert documents[0].episode == "Episode 1"


def test_long_transcript_splits_into_multiple_chunks():
    segments = [TranscriptSegment(text="x" * 600) for _ in range(3)]
    transcript = _transcript(segments)

    documents = chunk_transcript(transcript, episode="Episode 1", max_chunk_chars=1000)

    assert len(documents) > 1


def test_chunk_ids_are_stable_across_runs():
    transcript = _transcript([TranscriptSegment(text="Hello")])

    first_run = chunk_transcript(transcript, episode="Episode 1")
    second_run = chunk_transcript(transcript, episode="Episode 1")

    assert first_run[0].id == second_run[0].id


def test_chunk_ids_differ_by_source():
    transcript_a = _transcript([TranscriptSegment(text="Hello")], source="a.md")
    transcript_b = _transcript([TranscriptSegment(text="Hello")], source="b.md")

    documents_a = chunk_transcript(transcript_a, episode="Episode 1")
    documents_b = chunk_transcript(transcript_b, episode="Episode 1")

    assert documents_a[0].id != documents_b[0].id


def test_mixed_speaker_chunk_has_no_single_attributed_speaker():
    segments = [
        TranscriptSegment(text="Hi", speaker="Lenny"),
        TranscriptSegment(text="Hey", speaker="Jane"),
    ]
    transcript = _transcript(segments)

    documents = chunk_transcript(transcript, episode="Episode 1")

    assert documents[0].speaker is None


def test_timestamp_range_spans_first_to_last():
    segments = [
        TranscriptSegment(text="Hi", timestamp="00:00:01"),
        TranscriptSegment(text="Hey", timestamp="00:00:45"),
    ]
    transcript = _transcript(segments)

    documents = chunk_transcript(transcript, episode="Episode 1")

    assert documents[0].timestamp_range == "00:00:01–00:00:45"


def test_empty_transcript_produces_no_chunks():
    transcript = _transcript([])

    documents = chunk_transcript(transcript, episode="Episode 1")

    assert documents == []
