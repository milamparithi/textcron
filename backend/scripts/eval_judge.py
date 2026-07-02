#!/usr/bin/env python3
"""LLM-as-Judge evaluation for TextCron.

Usage:
    python scripts/eval_judge.py                        # all entries, default judge
    python scripts/eval_judge.py --sample 5              # random 5 entries
    python scripts/eval_judge.py --judge-model "anthropic/claude-sonnet-4-20250514"
    python scripts/eval_judge.py --output report.json
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from litellm import completion

from judge_prompt import JUDGE_SYSTEM_PROMPT, build_judge_prompt

BACKEND_DIR = Path(__file__).parent.parent
DATASET_PATH = BACKEND_DIR / "tests" / "golden_dataset.json"
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "scripts" / "eval_results"

# Load .env early so os.getenv works during arg defaults
env_path = BACKEND_DIR.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return json.load(f)


def _eligible_for_real_llm(entry: dict) -> bool:
    """Entries that make sense to evaluate with a real LLM."""
    if entry.get("mock_raises"):
        return False
    if entry.get("mock") and ("error" in entry["mock"]):
        return False
    if entry.get("mock") and entry["expected"]["status"] == 502:
        return False
    return True


def call_judge(prompt: str, model: str, api_key: str | None, timeout: int = 30, retries: int = 2,
               fallback_model: str | None = None, fallback_api_key: str | None = None) -> dict | None:
    import time as _time
    for attempt in range(1 + retries):
        try:
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                api_key=api_key,
                temperature=0.0,
                timeout=timeout,
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except Exception:
            if attempt < retries:
                _time.sleep(2 ** attempt)
                continue
    # All retries exhausted – try fallback model
    if fallback_model and fallback_model != model:
        print(f"  Judge model failed, falling back to {fallback_model}")
        try:
            response = completion(
                model=fallback_model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                api_key=fallback_api_key,
                temperature=0.0,
                timeout=timeout,
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except Exception:
            pass
    return None


def resolve_judge_model(provider: str, model: str) -> str:
    prefix_map = {
        "gemini": "gemini/",
        "google": "gemini/",
        "anthropic": "anthropic/",
        "groq": "groq/",
        "openai": "",
        "azure": "",
    }
    prefix = prefix_map.get(provider, "")
    if prefix and not model.startswith(prefix):
        return prefix + model
    return model


def evaluate_entry(
    entry: dict,
    client,
    judge_model: str,
    judge_api_key: str | None,
    judge_retries: int = 2,
    fallback_model: str | None = None,
    fallback_api_key: str | None = None,
) -> dict:
    name = entry["name"]
    text = entry["text"]
    expected = entry["expected"]

    # Step 1: Call the system via TestClient
    t0 = time.time()
    resp = client.post("/api/translate", json={"text": text})
    status = resp.status_code
    body = resp.json()
    latency = round(time.time() - t0, 2)

    # Step 2: Build judge prompt
    prompt = build_judge_prompt(text, status, body)

    # Step 3: Call the judge (falls back to system model on rate limits)
    t0 = time.time()
    verdict = call_judge(prompt, judge_model, judge_api_key, retries=judge_retries,
                         fallback_model=fallback_model, fallback_api_key=fallback_api_key)
    judge_latency = round(time.time() - t0, 2)

    # Step 4: Check if status matches expected
    status_match = status == expected["status"]

    result = {
        "entry": name,
        "text": text,
        "expected_status": expected["status"],
        "actual_status": status,
        "body": body,
        "status_match": status_match,
        "latency_s": latency,
        "judge_latency_s": judge_latency,
        "judge_error": verdict is None,
    }

    if verdict:
        scores = verdict.get("scores", {})
        result["scores"] = scores
        result["llm_pass"] = verdict.get("pass", False)
        result["justification"] = verdict.get("justification", "")
        # Programmatic pass: for error responses, error_handling must be perfect;
        # for success responses, cron must be correct and average >= 3
        cron = scores.get("cron_correctness", 0)
        err = scores.get("error_handling", 0)
        avg = sum(scores.values()) / max(len(scores), 1)
        if status >= 400:
            result["judge_pass"] = err >= 4
        else:
            result["judge_pass"] = cron >= 4 and err >= 3 and avg >= 3.0
    else:
        result["scores"] = {}
        result["llm_pass"] = False
        result["judge_pass"] = False
        result["justification"] = "Judge call failed"

    return result


def main():
    # Resolve defaults after .env is loaded
    default_judge_provider = os.getenv("JUDGE_PROVIDER") or os.getenv("LLM_PROVIDER") or "google"
    default_judge_model = os.getenv("JUDGE_MODEL") or ""
    default_judge_api_key = os.getenv("JUDGE_API_KEY") or os.getenv("LLM_API_KEY")

    parser = argparse.ArgumentParser(description="LLM-as-Judge evaluation for TextCron")
    parser.add_argument("--sample", type=int, default=None,
                        help="Number of random entries to evaluate (default: all; capped at 5 when omitted)")
    parser.add_argument("--judge-provider", default=default_judge_provider,
                        help="Judge LLM provider")
    parser.add_argument("--judge-model", default=default_judge_model,
                        help="Judge LLM model (default: a more capable model from the provider)")
    parser.add_argument("--judge-api-key", default=default_judge_api_key,
                        help="Judge API key (default: $JUDGE_API_KEY or $LLM_API_KEY)")
    parser.add_argument("--judge-delay", type=float, default=1.5,
                        help="Seconds to wait between judge calls to avoid rate limits (default: 1.5)")
    parser.add_argument("--judge-retries", type=int, default=2,
                        help="Retries per judge call on failure (default: 2)")
    parser.add_argument("--output", type=str, default="",
                        help=f"Output report path (default: eval_results/report_<timestamp>.json)")
    parser.add_argument("--quiet", action="store_true", help="Only print final summary")
    args = parser.parse_args()

    # Resolve judge model — default to a capable model
    judge_model_raw = args.judge_model
    if not judge_model_raw:
        system_model = os.getenv("LLM_MODEL", "")
        provider_defaults = {
            "google": "gemini/" + (system_model or "gemini-2.0-flash"),
            "gemini": "gemini/" + (system_model or "gemini-2.0-flash"),
            "anthropic": "anthropic/claude-sonnet-4-20250514",
            "openai": system_model or "gpt-4o-mini",
            "groq": system_model or "groq/llama-3.3-70b-versatile",
        }
        judge_model_raw = provider_defaults.get(args.judge_provider, "gpt-4o-mini")
    judge_model = resolve_judge_model(args.judge_provider, judge_model_raw)
    judge_api_key = args.judge_api_key or None

    # Set up GEMINI_API_KEY for judge if needed
    if args.judge_provider in ("google", "gemini") and not os.getenv("GEMINI_API_KEY"):
        if judge_api_key:
            os.environ["GEMINI_API_KEY"] = judge_api_key

    # Load dataset — keep only entries that make sense with a real LLM
    dataset = load_dataset()
    entries = [e for e in dataset if _eligible_for_real_llm(e)]
    sample = args.sample
    if sample is None and len(entries) > 5:
        sample = 5
    if sample and sample < len(entries):
        entries = random.sample(entries, sample)

    # Create TestClient (in-process, no server needed)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import guard
    guard._ip_store.clear()
    guard._global_store.clear()
    client = TestClient(app)

    # Resolve fallback to system model (used when judge model is rate-limited)
    sys_provider = os.getenv("LLM_PROVIDER", "google")
    sys_model = os.getenv("LLM_MODEL", "")
    fallback_model = resolve_judge_model(sys_provider, sys_model) if sys_model else None
    fallback_api_key = os.getenv("LLM_API_KEY")

    if not args.quiet:
        print(f"Judge model: {judge_model}  (fallback: {fallback_model})")
        print(f"Entries: {len(entries)}")
        print()

    # Evaluate
    results = []
    for i, entry in enumerate(entries, 1):
        if not args.quiet:
            print(f"[{i}/{len(entries)}] {entry['name']} ... ", end="", flush=True)
        result = evaluate_entry(entry, client, judge_model, judge_api_key,
                                judge_retries=args.judge_retries,
                                fallback_model=fallback_model, fallback_api_key=fallback_api_key)
        results.append(result)
        if not args.quiet:
            status_str = "PASS" if result["status_match"] and result.get("judge_pass") else "FAIL"
            print(f"{status_str} (status={result['actual_status']}, "
                  f"scores={result['scores']}, "
                  f"llm_pass={result.get('llm_pass', '?')}, "
                  f"{result['latency_s']}s + {result['judge_latency_s']}s)")
        if i < len(entries) and args.judge_delay:
            time.sleep(args.judge_delay)

    # Aggregate
    total = len(results)
    status_match_count = sum(1 for r in results if r["status_match"])
    judge_pass_count = sum(1 for r in results if r.get("judge_pass"))
    llm_pass_count = sum(1 for r in results if r.get("llm_pass"))
    judge_error_count = sum(1 for r in results if r["judge_error"])

    avg_scores = {}
    score_keys = ["cron_correctness", "explanation_accuracy", "error_handling", "warning_detection"]
    for key in score_keys:
        vals = [r["scores"].get(key, 0) for r in results if r["scores"]]
        avg_scores[key] = round(sum(vals) / len(vals), 2) if vals else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "judge_model": judge_model,
            "fallback_model": fallback_model,
            "entries_requested": len(entries),
            "entries_completed": total,
        },
        "summary": {
            "status_match_rate": f"{status_match_count}/{total}",
            "judge_pass_rate": f"{judge_pass_count}/{total}",
            "llm_pass_rate": f"{llm_pass_count}/{total}",
            "judge_error_count": judge_error_count,
            "avg_scores": avg_scores,
        },
        "results": results,
    }

    # Write report
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output or str(output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print()
    print("=" * 50)
    print(f"Report: {output_path}")
    print(f"Status match: {report['summary']['status_match_rate']}")
    print(f"Judge pass:   {report['summary']['judge_pass_rate']}")
    print(f"Avg scores:   {avg_scores}")
    print("=" * 50)


if __name__ == "__main__":
    main()
