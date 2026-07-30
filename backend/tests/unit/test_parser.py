from app.infrastructure.ingestion.parser import parse_markdown_transcript

TRANSCRIPT = """# Growth Loops 101

**Source:** https://github.com/org/lennys-podcast-transcripts/ep01.md

**[00:00:12] Lenny:** Welcome to the show.

**[00:01:03] Jane Doe:** Thanks for having me.

Just a plain paragraph with no speaker prefix.
"""


def test_extracts_title_from_heading():
    result = parse_markdown_transcript(TRANSCRIPT)

    assert result.title == "Growth Loops 101"


def test_extracts_source_from_metadata_line():
    result = parse_markdown_transcript(TRANSCRIPT)

    assert result.source == "https://github.com/org/lennys-podcast-transcripts/ep01.md"


def test_falls_back_to_default_source_when_missing():
    result = parse_markdown_transcript("# No source here\n\nSome text.", default_source="fallback.md")

    assert result.source == "fallback.md"


def test_extracts_speaker_and_timestamp_segments():
    result = parse_markdown_transcript(TRANSCRIPT)

    speaker_segments = [s for s in result.segments if s.speaker]
    assert [s.speaker for s in speaker_segments] == ["Lenny", "Jane Doe"]
    assert [s.timestamp for s in speaker_segments] == ["00:00:12", "00:01:03"]
    assert speaker_segments[0].text == "Welcome to the show."


def test_plain_paragraph_has_no_speaker_or_timestamp():
    result = parse_markdown_transcript(TRANSCRIPT)

    plain = next(s for s in result.segments if s.text.startswith("Just a plain"))
    assert plain.speaker is None
    assert plain.timestamp is None


def test_missing_title_falls_back_to_default():
    result = parse_markdown_transcript("Just body text, no heading.")

    assert result.title == "Untitled Episode"
