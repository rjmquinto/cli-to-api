import asyncio
import contextlib
import json
import os
import signal
import tempfile
from dataclasses import dataclass

from cli_to_api.clis.base import CLIError


@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: bytes
    stderr: bytes


async def run_cli(
    name: str,
    command: list[str],
    *,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
) -> Completed:
    """Run `command` in a fresh empty working directory and wait for it.

    `stdin` is written to the process; without it, stdin is /dev/null. If the
    awaiting task is cancelled, the process and anything it spawned are
    killed before the cancellation propagates.
    """
    with tempfile.TemporaryDirectory(prefix=f"cli-to-api-{name}-") as workdir:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=env,
                start_new_session=True,
            )
        except OSError as exc:
            raise CLIError(
                f"Could not run {name} executable {command[0]!r}: {exc.strerror or exc}."
            ) from exc

        try:
            stdout, stderr = await process.communicate(stdin)
        except asyncio.CancelledError:
            # Kill the whole process group in case the CLI spawned children.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            raise

    return Completed(process.returncode, stdout, stderr)


def exit_error(name: str, completed: Completed) -> CLIError:
    """Build the error for a non-zero exit that produced no usable message."""
    detail = tail(completed.stderr)
    return CLIError(
        f"{name} exited with status {completed.returncode}"
        + (f": {detail}" if detail else ".")
    )


def json_object(data: bytes) -> dict | None:
    """Parse `data` as a JSON object, or return None if it isn't one."""
    try:
        payload = json.loads(data)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def tail(data: bytes, lines: int = 5) -> str:
    text = data.decode(errors="replace").strip()
    return "\n".join(text.splitlines()[-lines:])
