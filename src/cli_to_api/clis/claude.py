import os

from cli_to_api.clis.base import CLI, CLIError
from cli_to_api.clis.process import Completed, exit_error, json_object, run_cli

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Answer the user's question."


class ClaudeCLI(CLI):
    """Answers questions with Claude Code's non-interactive mode (`claude -p`).

    With `api_key`, the CLI runs in `--bare` mode authenticated by that key,
    which skips CLAUDE.md discovery, hooks, plugins and auto-memory. Without
    it, the CLI uses the server's existing `claude` login, and any inherited
    ANTHROPIC_API_KEY is removed so billing depends only on `api_key`.

    Each query runs with tools disabled, in a fresh empty working directory,
    with the question passed on stdin.

    Known limitation of the login mode: the CLI still gives the model the
    logged-in account's email and basic environment info (OS, working
    directory), so a caller can get the model to reveal them. Use `api_key`
    where that matters.
    """

    name = "claude"

    def __init__(
        self,
        models: list[str],
        *,
        executable: str = "claude",
        api_key: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._models = list(models)
        self._executable = executable
        self._api_key = api_key
        self._system_prompt = system_prompt

    def supported_models(self) -> list[str]:
        return list(self._models)

    async def query(self, question: str, model: str) -> str:
        completed = await run_cli(
            self.name, self._command(model), stdin=question.encode(), env=self._env()
        )
        return self._parse(completed)

    def _command(self, model: str) -> list[str]:
        command = [
            self._executable,
            "-p",
            "--output-format", "json",
            "--model", model,
            "--tools", "",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--system-prompt", self._system_prompt,
        ]
        if self._api_key is not None:
            command.append("--bare")
        else:
            command += ["--setting-sources", ""]
        return command

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self._api_key is not None:
            env["ANTHROPIC_API_KEY"] = self._api_key
        else:
            env.pop("ANTHROPIC_API_KEY", None)
        return env

    def _parse(self, completed: Completed) -> str:
        payload = json_object(completed.stdout)
        result = payload.get("result") if payload else None

        if completed.returncode == 0 and isinstance(result, str) and not payload.get("is_error"):
            return result

        if isinstance(result, str) and result:
            raise CLIError(result)
        if completed.returncode != 0:
            raise exit_error(self.name, completed)
        if payload and payload.get("is_error"):
            raise CLIError(f"claude reported an error ({payload.get('subtype', 'unknown')}).")
        raise CLIError("Unexpected output from claude.")
