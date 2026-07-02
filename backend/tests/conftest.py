import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app


def pytest_addoption(parser):
    parser.addoption(
        "--real-llm",
        action="store_true",
        default=False,
        help="Call the real LLM instead of mocking it",
    )
    parser.addoption(
        "--sample",
        type=int,
        default=None,
        help="Run N random tests from the golden dataset (default: all; --real-llm defaults to 5)",
    )


@pytest.fixture(scope="session", autouse=True)
def _load_env(request):
    if request.config.getoption("--real-llm"):
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_rate_limits():
    from app.services import guard
    guard._ip_store.clear()
    guard._global_store.clear()
