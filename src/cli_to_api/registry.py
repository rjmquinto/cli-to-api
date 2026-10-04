from collections.abc import Sequence

from cli_to_api.clis import CLI


class UnknownModelError(Exception):
    """No registered CLI supports the requested model."""


class CLIRegistry:
    """Routes a model identifier to the CLI that supports it."""

    def __init__(self, clis: Sequence[CLI]) -> None:
        owners: dict[str, str] = {}
        for cli in clis:
            for model in cli.supported_models():
                if model in owners:
                    raise ValueError(
                        f"Model {model!r} is supported by both "
                        f"{owners[model]!r} and {cli.name!r}."
                    )
                owners[model] = cli.name
        self._clis = list(clis)

    def resolve(self, model: str) -> CLI:
        for cli in self._clis:
            if cli.supports(model):
                return cli
        raise UnknownModelError(f"Model {model!r} is not configured.")

    def models(self) -> dict[str, list[str]]:
        return {cli.name: cli.supported_models() for cli in self._clis}
