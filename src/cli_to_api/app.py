import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from cli_to_api.clis import CLIError
from cli_to_api.rate_limit import RateLimitedError
from cli_to_api.registry import CLIRegistry, UnknownModelError


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    model: str = Field(min_length=1)


class QueryResponse(BaseModel):
    answer: str
    model: str
    duration_ms: int


def error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def create_app(registry: CLIRegistry, *, timeout_s: float = 120) -> FastAPI:
    app = FastAPI(title="cli-to-api", version="0.1.0")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        return error_response(400, "invalid_request", f"{field}: {first['msg']}")

    @app.exception_handler(Exception)
    async def internal_error(_: Request, exc: Exception) -> JSONResponse:
        # Starlette re-raises after this handler, so the server logs the traceback.
        return error_response(500, "internal_error", "Internal server error.")

    @app.post("/query", response_model=QueryResponse)
    async def query(request: QueryRequest) -> QueryResponse | JSONResponse:
        try:
            cli = registry.resolve(request.model)
        except UnknownModelError as exc:
            return error_response(400, "unknown_model", str(exc))

        started = time.perf_counter()
        try:
            answer = await asyncio.wait_for(
                cli.query(request.question, request.model), timeout_s
            )
        except TimeoutError:
            return error_response(
                504, "timeout", f"Model did not respond within {timeout_s:g}s."
            )
        except RateLimitedError as exc:
            return error_response(
                429, "rate_limited", str(exc), headers={"Retry-After": str(exc.retry_after)}
            )
        except CLIError as exc:
            return error_response(500, "upstream_error", str(exc))
        duration_ms = round((time.perf_counter() - started) * 1000)

        return QueryResponse(answer=answer, model=request.model, duration_ms=duration_ms)

    return app
