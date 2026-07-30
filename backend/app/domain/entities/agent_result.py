from dataclasses import dataclass, field

from app.domain.entities.artifact import Artifact


@dataclass
class AgentResult:
    """Harness return type — keeps SDK message objects out of the inner layers."""

    text: str
    citations: list[str] = field(default_factory=list)
    artifact: Artifact | None = None
