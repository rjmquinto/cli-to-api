from cli_to_api.clis.base import CLI, CLIError
from cli_to_api.clis.process import Completed, exit_error, json_object, run_cli


class AntigravityCLI(CLI):
    """Answers questions with Google Antigravity CLI's headless mode (`agy -p`).

    Untested against a real `agy`; written from the docs at
    https://antigravity.google/docs/cli/headless/.

    Each query runs in a fresh empty working directory without
    `--dangerously-skip-permissions`, so tools that need approval are
    soft-denied: the run continues without them.

    Authentication is the server's cached `agy` login; the CLI documents no
    API key option. Antigravity only takes plain prompts as an argument, so
    unlike the other CLIs the question is visible to local users via `ps` and
    is limited by the OS's per-argument size limit (128 KiB on Linux).
    """

    name = "antigravity"

    def __init__(self, models: list[str], *, executable: str = "agy") -> None:
        self._models = list(models)
        self._executable = executable

    def supported_models(self) -> list[str]:
        return list(self._models)

    async def query(self, question: str, model: str) -> str:
        completed = await run_cli(self.name, self._command(question, model))
        return self._parse(completed)

    def _command(self, question: str, model: str) -> list[str]:
        return [
            self._executable,
            # `=` keeps a question starting with "-" from being read as a flag.
            f"--prompt={question}",
            "--output-format", "json",
            "--model", model,
        ]

    def _parse(self, completed: Completed) -> str:
        # Documented shape: {"status": "SUCCESS" | "ERROR" | ..., "response": str,
        # "error"?: str, ...}.
        payload = json_object(completed.stdout)
        status = payload.get("status") if payload else None
        response = payload.get("response") if payload else None
        error = payload.get("error") if payload else None

        if completed.returncode == 0 and status == "SUCCESS" and isinstance(response, str):
            return response

        if isinstance(error, str) and error:
            raise CLIError(error)
        if completed.returncode != 0:
            raise exit_error(self.name, completed)
        if status is not None:
            raise CLIError(f"antigravity run ended with status {status}.")
        raise CLIError("Unexpected output from antigravity.")
