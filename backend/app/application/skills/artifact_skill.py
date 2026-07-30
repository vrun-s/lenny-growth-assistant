"""Plain callable — no SDK import (per ARCHITECTURE.md §4.7).

Placeholder until artifact persistence (an IArtifactRepository port) exists.
Not wired to any fake persistence — this file exists so the skill's interface
contract is in place before the real implementation lands.
"""


def generate_artifact(artifact_type: str, content: str) -> dict:
    raise NotImplementedError(
        "generate_artifact is a placeholder. Implement validation + persistence "
        "once an IArtifactRepository port exists."
    )
