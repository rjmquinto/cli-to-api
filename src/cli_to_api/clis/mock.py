import asyncio

from cli_to_api.clis.base import CLI, CLIError


class MockCLI(CLI):
    """A stand-in CLI that answers without running anything.

    `delay` and `error` simulate slow and failing CLIs.
    """

    def __init__(
        self,
        name: str,
        models: list[str],
        *,
        answer: str | None = None,
        delay: float = 0.0,
        error: str | None = None,
    ) -> None:
        self.name = name
        self._models = list(models)
        self._answer = answer
        self._delay = delay
        self._error = error

    def supported_models(self) -> list[str]:
        return list(self._models)

    async def query(self, question: str, model: str) -> str:
        await asyncio.sleep(self._delay)
        if self._error is not None:
            raise CLIError(self._error)
        if self._answer is not None:
            return self._answer
        return f"[mock {self.name}/{model}] {question}"
