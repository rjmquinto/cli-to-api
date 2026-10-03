import os

from cli_to_api.clis.base import CLI, CLIError
from cli_to_api.clis.process import Completed, exit_error, json_object, run_cli

# Codex features that would let the model act beyond answering: run commands,
# read local files or images, browse, use plugins/apps, spawn agents, or
# remember across runs. `codex exec` rejects unknown names, so a feature
# renamed upstream fails every query loudly instead of silently staying on.
DISABLED_FEATURES = [
    "shell_tool",
    "unified_exec",
    "view_image",
    "browser_use",
    "computer_use",
    "plugins",
    "apps",
    "multi_agent",
    "image_generation",
    "memories",
]


class CodexCLI(CLI):
    """Answers questions with OpenAI Codex CLI's non-interactive mode (`codex exec`).

    Untested against a real authenticated `codex`; flags are from
    `codex exec --help` (0.160.0) and the event format from
    https://learn.chatgpt.com/docs/non-interactive-mode.

    The question is passed on stdin. Each query runs in a fresh empty working
    directory, in the read-only sandbox, without the user's config.toml or
    rules, without saving a session, and with the features in
    DISABLED_FEATURES turned off. The read-only sandbox blocks writes but not
    reads, so disabling the shell and file tools is what keeps a caller from
    getting the model to read files such as Codex's stored credentials.

    With `api_key`, the CLI is given CODEX_API_KEY. Without it, inherited
    CODEX_API_KEY and OPENAI_API_KEY are removed and the CLI uses the
    server's `codex login`.
    """

    name = "codex"

    def __init__(
        self,
        models: list[str],
        *,
        executable: str = "codex",
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
        command = [
            self._executable,
            "exec",
            "--json",
            "--model", model,
            "--sandbox", "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--color", "never",
        ]
        for feature in DISABLED_FEATURES:
            command += ["--disable", feature]
        command.append("-")  # read the prompt from stdin
        return command

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("OPENAI_API_KEY", None)
        if self._api_key is not None:
            env["CODEX_API_KEY"] = self._api_key
        else:
            env.pop("CODEX_API_KEY", None)
        return env

    def _parse(self, completed: Completed) -> str:
        # JSONL events. The answer is the last completed agent_message item;
        # failures arrive as {"type": "turn.failed", "error": {"message": ...}}
        # and/or {"type": "error", "message": ...}.
        answer = turn_failure = last_error = None
        for line in completed.stdout.splitlines():
            event = json_object(line)
            if event is None:
                continue
            kind = event.get("type")
            item = event.get("item")
            if kind == "item.completed" and isinstance(item, dict):
                if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                    answer = item["text"]
            elif kind == "turn.failed":
                error = event.get("error")
                if isinstance(error, dict) and error.get("message"):
                    turn_failure = str(error["message"])
            elif kind == "error" and event.get("message"):
                last_error = str(event["message"])

        if completed.returncode == 0 and answer is not None and turn_failure is None:
            return answer

        if turn_failure or last_error:
            raise CLIError(turn_failure or last_error)
        if completed.returncode != 0:
            raise exit_error(self.name, completed)
        raise CLIError("Unexpected output from codex.")
