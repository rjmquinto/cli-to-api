import os

from cli_to_api.clis.base import CLI, CLIError
from cli_to_api.clis.process import Completed, exit_error, json_object, run_cli


class GeminiCLI(CLI):
    """Answers questions with Gemini CLI's headless mode.

    Untested against a real `gemini`; written from the docs at
    https://geminicli.com/docs/cli/headless.

    The question is piped on stdin, which puts the CLI in headless mode. Each
    query runs in a fresh empty working directory with
    `--approval-mode default`, so tools that need confirmation can't run.

    `--skip-trust` trusts that directory for the run. Headless mode exits with
    FatalUntrustedWorkspaceError in an untrusted folder when folder trust is
    enabled, and a fresh directory is never on the trusted list. Trust only
    unlocks loading workspace settings, .env, MCP servers and commands, and
    the directory is empty.

    With `api_key`, the CLI is given GEMINI_API_KEY. Without it, any inherited
    GEMINI_API_KEY is removed and the CLI uses the server's cached login.
    Gemini CLI does not document which wins when a key and a cached login
    both exist, so a cached login may take precedence over `api_key`.
    """

    name = "gemini"

    def __init__(
        self,
        models: list[str],
        *,
        executable: str = "gemini",
        api_key: str | None = None,
    ) -> None:
        self._models = list(models)
        self._executable = executable
        self._api_key = api_key

    def supported_models(self) -> list[str]:
        return list(self._models)

    async def query(self, question: str, model: str) -> str:
        completed = await run_cli(
            self.name, self._command(model), stdin=question.encode(), env=self._env()
        )
        return self._parse(completed)

    def _command(self, model: str) -> list[str]:
        return [
            self._executable,
            "--output-format", "json",
            "--model", model,
            "--approval-mode", "default",
            "--skip-trust",
        ]

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self._api_key is not None:
            env["GEMINI_API_KEY"] = self._api_key
        else:
            env.pop("GEMINI_API_KEY", None)
        return env

    def _parse(self, completed: Completed) -> str:
        # Documented shape: {"response": str, "stats": {...}, "error"?: {...}}.
        payload = json_object(completed.stdout)
        response = payload.get("response") if payload else None
        error = payload.get("error") if payload else None

        if completed.returncode == 0 and isinstance(response, str) and not error:
            return response

        if isinstance(error, dict) and error.get("message"):
            raise CLIError(str(error["message"]))
        if isinstance(error, str) and error:
            raise CLIError(error)
        if completed.returncode != 0:
            raise exit_error(self.name, completed)
        raise CLIError("Unexpected output from gemini.")
