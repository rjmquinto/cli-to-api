import pytest
from fastapi.testclient import TestClient

from cli_to_api.app import create_app
from cli_to_api.clis import MockCLI
from cli_to_api.registry import CLIRegistry


def client_for(*clis: MockCLI, timeout_s: float = 5) -> TestClient:
    return TestClient(create_app(CLIRegistry(clis), timeout_s=timeout_s))


def test_returns_answer_and_metadata():
    client = client_for(MockCLI("claude", ["claude-a"], answer="Paris."))

    response = client.post("/query", json={"question": "Capital?", "model": "claude-a"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Paris."
    assert body["model"] == "claude-a"
    assert body["duration_ms"] >= 0


def test_unknown_model():
    client = client_for(MockCLI("claude", ["claude-a"]))

    response = client.post("/query", json={"question": "hi", "model": "gpt-9"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_model"


@pytest.mark.parametrize(
    "body",
    [
        {"question": "", "model": "claude-a"},
        {"model": "claude-a"},
        {"question": "hi", "model": "claude-a", "extra": 1},
    ],
    ids=["empty-question", "missing-field", "extra-field"],
)
def test_invalid_request(body):
    client = client_for(MockCLI("claude", ["claude-a"]))

    response = client.post("/query", json=body)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_malformed_json():
    client = client_for(MockCLI("claude", ["claude-a"]))

    response = client.post(
        "/query", content="{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_cli_failure():
    client = client_for(MockCLI("claude", ["claude-a"], error="CLI exited with status 1."))

    response = client.post("/query", json={"question": "hi", "model": "claude-a"})

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "upstream_error", "message": "CLI exited with status 1."}
    }


def test_unexpected_error():
    class BrokenCLI(MockCLI):
        async def query(self, question: str, model: str) -> str:
            raise FileNotFoundError("claude: command not found")

    client = TestClient(
        create_app(CLIRegistry([BrokenCLI("claude", ["claude-a"])])),
        raise_server_exceptions=False,
    )

    response = client.post("/query", json={"question": "hi", "model": "claude-a"})

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error."}
    }


def test_timeout():
    client = client_for(MockCLI("claude", ["claude-a"], delay=1), timeout_s=0.05)

    response = client.post("/query", json={"question": "hi", "model": "claude-a"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "timeout"
