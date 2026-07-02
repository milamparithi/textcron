import json
import random
import pytest
from pathlib import Path

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


def load_dataset():
    with open(DATASET_PATH) as f:
        return json.load(f)


def _make_test_id(entry: dict) -> str:
    return entry["name"].replace(" ", "_").replace("(", "").replace(")", "").replace(">", "gt").replace("<", "lt")


def _must_skip_with_real_llm(entry: dict) -> bool:
    """True if this entry requires a specific mock response that a real LLM won't produce."""
    if entry.get("mock_raises"):
        return True
    if entry.get("mock") and ("error" in entry["mock"]):
        return True
    if entry.get("mock") and entry["expected"]["status"] == 502:
        return True
    return False


def _is_input_validation_test(entry: dict) -> bool:
    """True if the test fails at validate_input, before LLM is ever called."""
    return entry.get("mock") is None and not entry.get("mock_raises", False)


def pytest_generate_tests(metafunc):
    if "golden_entry" not in metafunc.fixturenames:
        return

    dataset = load_dataset()
    use_real_llm = metafunc.config.getoption("--real-llm")
    sample_size = metafunc.config.getoption("--sample")

    if use_real_llm:
        dataset = [e for e in dataset if not _must_skip_with_real_llm(e)]
        if sample_size is None:
            sample_size = 5

    if sample_size and sample_size < len(dataset):
        dataset = random.sample(dataset, sample_size)

    metafunc.parametrize("golden_entry", dataset, ids=_make_test_id)


def test_golden(request, client, monkeypatch, golden_entry):
    from app.services import llm as llm_module
    from app.services.llm import LlmResult

    use_real_llm = request.config.getoption("--real-llm")
    expected = golden_entry["expected"]

    # --- Mock LLM (only when not using real LLM) ---
    if not use_real_llm:
        if golden_entry.get("mock_raises"):
            def raises(*a, **kw):
                raise Exception("LLM failed")
            monkeypatch.setattr(llm_module, "translate", raises)
        elif golden_entry["mock"] is not None:
            def fake(text):
                return LlmResult(parsed=dict(golden_entry["mock"]), model="test-model")
            monkeypatch.setattr(llm_module, "translate", fake)

    # --- Execute ---
    resp = client.post("/api/translate", json={"text": golden_entry["text"]})
    body = resp.json()

    # --- Assert status ---
    assert resp.status_code == expected["status"], (
        f"Expected status {expected['status']}, got {resp.status_code}. Body: {resp.text[:300]}"
    )

    # --- Assert checks (same logic regardless of mock/real — real LLM must match expected) ---
    for check in expected.get("checks", []):
        typ = check["type"]
        val = check["value"]

        if typ == "detail_contains":
            detail = body.get("detail", "")
            assert val in detail, f"Expected detail to contain {val!r}, got {detail!r}"
        elif typ == "detail_not_contains":
            detail = body.get("detail", "")
            assert val not in detail, f"Expected detail to NOT contain {val!r}, got {detail!r}"
        elif typ == "cron":
            assert body["cron"] == val, f"Expected cron {val!r}, got {body['cron']!r}"
        elif typ == "warning":
            assert body["warning"] == val, f"Expected warning {val!r}, got {body['warning']!r}"
        elif typ == "warning_contains":
            assert val in body["warning"], f"Expected warning to contain {val!r}, got {body['warning']!r}"
        elif typ == "body_has_key":
            assert val in body, f"Expected body to have key {val!r}, keys: {list(body.keys())}"
        elif typ == "body_not_has_key":
            assert val not in body, f"Expected body to NOT have key {val!r}"
        elif typ == "cron_valid":
            parts = body["cron"].split()
            assert len(parts) == 5, f"Invalid cron expression: {body['cron']!r}"
        elif typ == "explanation_not_empty":
            assert len(body.get("explanation", "")) > 0, "Explanation is empty"
        else:
            raise ValueError(f"Unknown check type: {typ}")
