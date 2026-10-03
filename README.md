# cli-to-api
This service exposes certain CLI applications as a web API

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                          # install dependencies
uv run pytest                                    # run tests
uv run uvicorn cli_to_api.main:app --port 8080   # run the server
```

```sh
curl -s localhost:8080/query -H 'content-type: application/json' \
  -d '{"question": "What is the capital of France?", "model": "claude-sonnet-5-5"}'
```

The API is described in [openapi.yaml](openapi.yaml). CLIs and their model lists are
wired up in `src/cli_to_api/main.py`. A model routes to the CLI that lists it; if that CLI
isn't installed, queries for it return `500 upstream_error`.

### Claude

Requires Claude Code (`claude`) installed. Configure with environment variables:

| Variable | Purpose |
|---|---|
| `CLAUDE_CLI` | Path to the `claude` executable (default: `claude` on `PATH`) |
| `ANTHROPIC_API_KEY` | If set, queries run in `--bare` mode billed to this key. If unset, they use the server's existing `claude` login. |

Login mode is less isolated: the model can see the logged-in account's email and basic
environment info, and a caller can ask it to repeat them. Prefer `ANTHROPIC_API_KEY` for
anything exposed beyond a trusted network.

`uv run pytest` uses a fake `claude`. To run one real query:

```sh
CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py
```

### Gemini (untested)

Requires [Gemini CLI](https://geminicli.com/) (`gemini`). Written from its docs; not yet
run against the real CLI.

| Variable | Purpose |
|---|---|
| `GEMINI_CLI` | Path to the `gemini` executable (default: `gemini` on `PATH`) |
| `GEMINI_API_KEY` | If set, passed to the CLI. If unset, the CLI uses its cached login. |

Gemini CLI doesn't document whether an API key or a cached login wins when both exist.
Free-tier and Google One accounts were moved from Gemini CLI to Antigravity CLI on
2026-06-18.

### Antigravity (untested)

Requires [Antigravity CLI](https://antigravity.google/docs/cli/headless/) (`agy`),
logged in once interactively. Written from its docs; not yet run against the real CLI.

| Variable | Purpose |
|---|---|
| `ANTIGRAVITY_CLI` | Path to the `agy` executable (default: `agy` on `PATH`) |

Antigravity has no documented API key option, and it only accepts the question as a
command-line argument: other local users can see questions via `ps`, and very long
questions (over 128 KiB on Linux) fail.
