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
        """Return the models this CLI can query.

        Entries are exact model identifiers by default. They may instead be
        templates (e.g. `claude-*`), in which case the subclass must override
        `supports` to match against them.

        The registry rejects a model listed by two CLIs, but compares entries
        literally: overlapping templates across CLIs are not detected, and the
        first registered CLI whose `supports` matches wins.
        """

    def supports(self, model: str) -> bool:
        """Return whether this CLI can query `model`.

        Defaults to exact membership in `supported_models`. Override this
        when `supported_models` returns templates.
        """
        return model in self.supported_models()

    @abstractmethod
    async def query(self, question: str, model: str) -> str:
        """Ask `model` the `question` and return its answer."""
