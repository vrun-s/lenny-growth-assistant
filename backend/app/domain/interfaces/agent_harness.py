from abc import ABC, abstractmethod

from app.domain.entities.agent_result import AgentResult
from app.domain.entities.message import Message


class IAgentHarness(ABC):
    """The single port through which a use case reaches a model. Replaces the
    cancelled ILLMProvider abstraction — there is no per-vendor provider class,
    only this one port plus config (see docs/design.md).
    """

    @abstractmethod
    def run(self, history: list[Message], user_message: str) -> AgentResult:
        """Run one turn: prior messages plus the new user message in, an
        AgentResult out. Implementations own the agent loop; this port does not.
        """
        ...
