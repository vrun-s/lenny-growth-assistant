"""Parses raw Markdown transcript text into structured segments, preserving
speaker and timestamp metadata where the source encodes them.

Two source conventions are supported:

1. The original inline convention this parser was written against:

    # Episode Title

    **Source:** https://github.com/org/lennys-podcast-transcripts/ep01.md

    **[00:00:12] Lenny:** Welcome to the show...

    **[00:01:03] Jane Doe:** Thanks for having me...

2. The actual format used by the real corpus, the ChatPRD/lennys-podcast-transcripts
   archive (github.com/ChatPRD/lennys-podcast-transcripts): a YAML frontmatter
   block (`guest`, `title`, `youtube_url`, ...) followed by a body where each
   turn is a `Speaker (HH:MM:SS):` header line followed by the turn's text on
   the next line(s), e.g.:

    ---
    title: Some Episode Title
    youtube_url: https://www.youtube.com/watch?v=abc123
    ---

    # Some Episode Title

    ## Transcript

    Annie Duke (00:00:00):
    It's so incredibly necessary...

    (00:00:12):
    A continuation line with no speaker repeats the prior speaker.

Frontmatter `title`/`youtube_url` take precedence over the inline `# Title` /
`**Source:**` conventions when both are present. Lines that don't match either
segment convention are kept as plain paragraphs (speaker/timestamp left as
None), so free-form transcripts still parse instead of being dropped.
"""

import re
from dataclasses import dataclass

import yaml

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_SOURCE_RE = re.compile(r"^\*\*Source:\*\*\s*(\S+)", re.MULTILINE)
_INLINE_SEGMENT_RE = re.compile(
    r"^\*\*(?:\[(?P<timestamp>[\d:]+)\]\s*)?(?P<speaker>[^:*]+):\*\*\s*(?P<text>.+)$"
)
_SPEAKER_HEADER_RE = re.compile(
    r"^(?P<speaker>[^()\n]*?)\s*\((?P<timestamp>\d{1,2}(?::\d{2}){1,2})\):\s*$"
)
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n", re.DOTALL)


@dataclass
class TranscriptSegment:
    text: str
    speaker: str | None = None
    timestamp: str | None = None


@dataclass
class ParsedTranscript:
    title: str
    source: str
    segments: list[TranscriptSegment]


def _split_frontmatter(markdown: str) -> tuple[dict, str]:
    """Splits off a leading YAML frontmatter block, returning the parsed
    fields and the remaining body. Returns ({}, markdown) unchanged if there's
    no frontmatter block, so the original inline-only transcripts still parse
    exactly as before.
    """
    match = _FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    try:
        fields = yaml.safe_load(match.group("yaml")) or {}
    except yaml.YAMLError:
        fields = {}
    return (fields if isinstance(fields, dict) else {}), markdown[match.end() :]


def parse_markdown_transcript(markdown: str, *, default_source: str = "") -> ParsedTranscript:
    frontmatter, body = _split_frontmatter(markdown)

    title_match = _TITLE_RE.search(body)
    title = (
        frontmatter.get("title")
        or (title_match.group(1).strip() if title_match else None)
        or "Untitled Episode"
    )

    source_match = _SOURCE_RE.search(body)
    source = frontmatter.get("youtube_url") or (
        source_match.group(1).strip() if source_match else default_source
    )

    return ParsedTranscript(title=title, source=source, segments=_parse_segments(body))


def _parse_segments(body: str) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    last_speaker: str | None = None
    lines = body.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#") or line.startswith("**Source:**"):
            continue

        inline_match = _INLINE_SEGMENT_RE.match(line)
        if inline_match:
            speaker = inline_match.group("speaker").strip()
            segments.append(
                TranscriptSegment(
                    text=inline_match.group("text").strip(),
                    speaker=speaker,
                    timestamp=inline_match.group("timestamp"),
                )
            )
            last_speaker = speaker
            continue

        header_match = _SPEAKER_HEADER_RE.match(line)
        if header_match:
            speaker = header_match.group("speaker").strip() or last_speaker
            timestamp = header_match.group("timestamp")
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = " ".join(text_lines).strip()
            if text:
                segments.append(TranscriptSegment(text=text, speaker=speaker, timestamp=timestamp))
                last_speaker = speaker
            continue

        segments.append(TranscriptSegment(text=line))

    return segments
