import json
import os
from dataclasses import dataclass, field
from typing import Any

from litellm import completion


@dataclass
class LlmResult:
    """Result of an LLM translation call, including parsed output and usage metadata."""

    parsed: dict[str, Any]
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    prompt: list | None = None
    response_text: str = ""


SYSTEM_PROMPT = """You are a schedule parser. Convert natural language schedule descriptions into structured JSON fields.

If the input describes a valid cron-able schedule, output:
{"minute": "...", "hour": "...", "day_of_month": "...", "month": "...", "day_of_week": "...", "explanation": "..."}

If the input contains an impossible, invalid, unsupported, or ambiguous schedule, output:
{"error": "clear description of the problem"}

Valid output rules:
- Each field must be one of: *, a number, */N, a range (a-b), or a comma-separated list (a,b,c)
- minute: 0-59, hour: 0-23, day_of_month: 1-31, month: 1-12, day_of_week: 0=Sunday ... 6=Saturday
- For "every weekday" use day_of_week "1-5"
- For "every weekend" use day_of_week "0,6"

Detect and return an error for these cases:
1. Impossible dates — e.g. "February 30", "April 31", "31st November"
2. Invalid intervals — e.g. "every 0 minutes", "every -1 hours", "every 0 seconds"
3. Unsupported concepts — e.g. "fortnightly", "quarterly", "every other day", "every N months" where N>1, "even days only", "on the last weekday of the month", "every weekday except holidays"
4. Ambiguity — e.g. "every second day" (does it mean every 2 days or on the 2nd?), "every morning" / "every afternoon" / "every evening" (vague time of day — specify an exact time like 8am or 6pm), "mid-afternoon" (vague), "at noon" (noon is fine but be precise)

Return only the JSON object—no markdown, no backticks, no extra text.
Do NOT output a raw cron string anywhere in the response.

Valid examples:
Input: "every weekday at 3pm"
Output: {"minute": "0", "hour": "15", "day_of_month": "*", "month": "*", "day_of_week": "1-5", "explanation": "At 3:00 PM, Monday through Friday"}

Input: "every 5 minutes"
Output: {"minute": "*/5", "hour": "*", "day_of_month": "*", "month": "*", "day_of_week": "*", "explanation": "Every 5 minutes"}

Input: "at midnight on the first of every month"
Output: {"minute": "0", "hour": "0", "day_of_month": "1", "month": "*", "day_of_week": "*", "explanation": "At midnight, on day 1 of the month"}

Input: "every Sunday at 8am"
Output: {"minute": "0", "hour": "8", "day_of_month": "*", "month": "*", "day_of_week": "0", "explanation": "At 8:00 AM, on Sunday"}

Error examples:
Input: "every 0 minutes"
Output: {"error": "Interval of 0 minutes is invalid. Please specify a positive interval (e.g. every 5 minutes)."}

Input: "on February 30"
Output: {"error": "February never has 30 days. Please use a valid date."}

Input: "fortnightly"
Output: {"error": "'Fortnightly' schedules (every 14 days) are not supported. Try 'every 2 weeks on Monday' or specify exact dates."}

Input: "every second day"
Output: {"error": "Ambiguous: 'every second day' could mean every 2 days or on the 2nd of every month. Please clarify (e.g. 'every 2 days' or 'on the 2nd of each month')."}

Input: "every morning"
Output: {"error": "'Every morning' is ambiguous — morning spans several hours. Please specify an exact time (e.g. 'every day at 8am')."}
"""

PROVIDER_PREFIXES = {
    "gemini": "gemini/",
    "google": "gemini/",
    "anthropic": "anthropic/",
    "groq": "groq/",
    "openai": "",
    "azure": "",
}

PROVIDER_TEMPERATURE_SUPPORT = {"openai", "azure", "gemini", "google", "anthropic", "groq"}


def _resolve_model(provider: str, model: str) -> str:
    """Prepend provider prefix (e.g. gemini/ ) for litellm compatibility."""
    prefix = PROVIDER_PREFIXES.get(provider, "")
    if prefix and not model.startswith(prefix):
        return prefix + model
    return model


def _set_provider_env(provider: str):
    """Set provider-specific env vars (e.g. GEMINI_API_KEY) from LLM_API_KEY."""
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return
    if provider in ("gemini", "google") and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = api_key
    elif provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "groq" and not os.getenv("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = api_key


def translate(text: str) -> LlmResult:
    """Call the LLM to parse a natural language schedule into structured fields."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model = _resolve_model(provider, os.getenv("LLM_MODEL", "gpt-4o-mini"))
    api_key = os.getenv("LLM_API_KEY") or None
    base_url = os.getenv("LLM_BASE_URL") or None
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

    _set_provider_env(provider)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "api_key": api_key,
        "temperature": temperature,
    }

    if base_url:
        kwargs["base_url"] = base_url
    if provider in ("openai", "azure"):
        kwargs["response_format"] = {"type": "json_object"}

    response = completion(**kwargs, timeout=15.0)
    content = response.choices[0].message.content
    parsed = json.loads(content)

    usage = getattr(response, "usage", None)
    hidden = getattr(response, "_hidden_params", {})

    return LlmResult(
        parsed=parsed,
        model=getattr(response, "model", ""),
        prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
        input_cost=0.0,
        output_cost=0.0,
        total_cost=hidden.get("response_cost", 0.0) or 0.0,
        prompt=messages,
        response_text=content,
    )
