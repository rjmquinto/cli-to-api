from abc import ABC, abstractmethod


class CLIError(Exception):
    """The CLI failed or produced no usable answer."""


class CLI(ABC):
    """An LLM command-line tool that can answer questions.

    Subclasses implement `supported_models` and `query`. `query` must return
    the answer text and raise `CLIError` on failure. The server enforces its
    timeout by cancelling `query`, so implementations that spawn a subprocess
    must kill it when cancelled.
    """

    name: str

    @abstractmethod
    def supported_models(self) -> list[str]:
        """Return the model identifiers this CLI can query."""

    def supports(self, model: str) -> bool:
        return model in self.supported_models()

    @abstractmethod
    async def query(self, question: str, model: str) -> str:
        """Ask `model` the `question` and return its answer."""
