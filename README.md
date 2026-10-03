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

The API is described in [openapi.yaml](openapi.yaml). The CLIs are currently mocked
(see `src/cli_to_api/main.py`).
