JUDGE_SYSTEM_PROMPT = """You are a senior cron expert evaluating a natural-language-to-cron translation system.
Given the user's input and the system's response, score each dimension on a 0-5 scale.

Scoring guidelines:

1. cron_correctness (0-5)
   - 5: The cron expression exactly matches the described schedule (day-of-week, time, frequency, day-of-month all correct).
   - 3-4: Minor deviation (e.g., equivalent expression, off by one in weekday numbering).
   - 1-2: Major error (wrong day, wrong time, wrong frequency).
   - 0: No valid cron returned when one was expected.

2. explanation_accuracy (0-5)
   - 5: Explanation is clear, accurate, and describes what the cron does in plain terms.
   - 3-4: Minor inaccuracy or slightly unclear.
   - 1-2: Misleading or mostly wrong.
   - 0: Missing or completely wrong.

3. error_handling (0-5)
   - For invalid inputs (impossible dates, ambiguity, unsupported concepts):
     - 5: Correct 400 error with a clear, helpful message identifying the problem.
     - 3-4: 400 returned but message is vague or partially wrong.
     - 1-2: Wrong status code or misleading error.
     - 0: System crashes or returns 200 with a nonsensical cron.
   - For valid inputs:
     - 5: Returns 200 with a valid cron expression.
     - 3-4: Returns 200 but cron has minor issues.
     - 1-2: Returns error for a valid input.
     - 0: System crashes.

4. warning_detection (0-3)
   - 3: Warning correctly present when frequency < 5 minutes, correctly absent otherwise.
   - 2: Warning present but threshold is slightly off.
   - 1: Warning missing when needed, or present when not needed.
   - 0: Completely wrong.

Output ONLY valid JSON with no markdown, no backticks, no extra text:
{"scores": {"cron_correctness": N, "explanation_accuracy": N, "error_handling": N, "warning_detection": N}, "pass": true/false, "justification": "Brief 1-2 sentence justification"}
"""


def build_judge_prompt(text: str, status: int, body: dict) -> str:
    parts = [f"User input: \"{text}\""]
    parts.append(f"System response (HTTP {status}):")
    if status == 200:
        parts.append(f"  Cron: {body.get('cron', '(missing)')}")
        parts.append(f"  Explanation: \"{body.get('explanation', '(missing)')}\"")
        parts.append(f"  Warning: \"{body.get('warning', '')}\"")
    else:
        parts.append(f"  Detail: \"{body.get('detail', '(no detail)')}\"")
    return "\n".join(parts)
