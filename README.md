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

The API is described in [openapi.yaml](openapi.yaml). CLIs are wired up in
`src/cli_to_api/main.py`; Claude is real, Gemini is still mocked.

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
