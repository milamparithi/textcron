# Test Plan

## Backend (Python — pytest)

### Setup

Add to `backend/pyproject.toml`:
```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "httpx>=0.28",
    "pytest-asyncio>=0.24",
]
```

Run: `python -m pytest tests/ -v`

### Structure

```
backend/tests/
├── conftest.py                  # fixtures: test client, mock LLM
├── services/
│   ├── test_cron.py             # compose, is_valid, next_times
│   └── test_guard.py            # validate_input, validate_llm_output, check_cron_safety, rate_limit
└── api/
    └── test_translate.py        # POST /api/translate — success, error, validation, rate limit
```

### Unit Tests — `services/test_cron.py`

| Test | What it covers |
|------|----------------|
| `test_compose_joins_fields` | `compose({"minute":"0","hour":"15","day_of_month":"*","month":"*","day_of_week":"1-5"})` → `"0 15 * * 1-5"` |
| `test_compose_defaults_missing` | Missing field defaults to `*` |
| `test_compose_empty_string` | Empty string field defaults to `*` |
| `test_is_valid_good` | `"0 15 * * 1-5"` → `True` |
| `test_is_valid_bad` | `"bad"` → `False` |
| `test_next_times_returns_n` | Returns exactly N items |
| `test_next_times_format` | Each item matches `YYYY-MM-DD HH:MM UTC` |

### Unit Tests — `services/test_guard.py`

| Test | What it covers |
|------|----------------|
| `test_validate_input_ok` | `"every weekday at 3pm"` passes |
| `test_validate_input_empty` | Empty string raises 400 |
| `test_validate_input_too_long` | >500 chars raises 400 |
| `test_validate_input_disallowed_chars` | `<script>` raises 400 |
| `test_validate_input_no_time_keyword` | `"hello world"` raises 400 |
| `test_validate_input_gibberish` | Repetitive chars raise 400 |
| `test_validate_llm_output_good` | Valid fields pass |
| `test_validate_llm_output_error` | `{"error":"..."}` raises `LlmError` |
| `test_validate_llm_output_missing_field` | Missing field raises `LlmSystemError` |
| `test_validate_llm_output_out_of_range` | `minute: 99` raises `LlmSystemError` |
| `test_check_cron_safety_frequent` | `"* * * * *"` returns warning string |
| `test_check_cron_safety_ok` | `"0 15 * * 1-5"` returns `None` |
| `test_check_cron_safety_invalid` | `"bad"` raises `ValueError` |
| `test_rate_limit_per_ip` | 31st request from same IP in 60s returns 429 |
| `test_rate_limit_global` | 101st request overall returns 429 |

### API Tests — `api/test_translate.py`

| Test | What it covers |
|------|----------------|
| `test_translate_success` | Valid input → 200 with cron, explanation, warning fields |
| `test_translate_empty_body` | Missing text → 422 (Pydantic validation) |
| `test_translate_llm_error` | Mock LLM returning `{"error":"..."}` → 400 with message |
| `test_translate_llm_system_error` | Mock LLM returning out-of-range fields → 502 |
| `test_translate_frequent` | Mock LLM returning every-minute → 200 with warning |
| `test_translate_rate_limited` | Exhaust per-IP limit → 429 |

### Mocking Strategy

In `conftest.py`, patch `app.services.llm.translate` to return controlled JSON:

```python
@pytest.fixture
def mock_llm(monkeypatch):
    def fake_translate(text):
        return {
            "minute": "0", "hour": "15",
            "day_of_month": "*", "month": "*",
            "day_of_week": "1-5",
            "explanation": "Test"
        }
    monkeypatch.setattr("app.services.llm.translate", fake_translate)
```

No LLM calls during tests. Use `httpx.AsyncClient` with FastAPI's `TestClient` for endpoint tests.

---

## Frontend (React — Vitest + Testing Library)

### Setup

Add to `frontend/package.json`:
```json
"devDependencies": {
    "vitest": "^3.0",
    "@testing-library/react": "^16.0",
    "@testing-library/jest-dom": "^6.0",
    "jsdom": "^25.0"
}
```

Add to `frontend/vite.config.ts`:
```ts
/// <reference types="vitest" />
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
  // ...
});
```

Add script: `"test": "vitest run"`

### Structure

```
frontend/src/
├── test/
│   └── setup.ts              # @testing-library/jest-dom imports
├── components/
│   ├── CronBadge.test.tsx
│   ├── InputCard.test.tsx
│   ├── ResultCard.test.tsx
│   └── ErrorCard.test.tsx
├── hooks/
│   └── useTranslate.test.ts
└── api/
    └── cron.test.ts
```

### Hook Tests — `hooks/useTranslate.test.ts`

Use `renderHook` from `@testing-library/react`. Mock `api/cron.ts` with `vi.mock`.

| Test | What it covers |
|------|----------------|
| `initial state` | text empty, loading false, result null, error null |
| `handleSubmit calls translate and validate` | Both API functions called with correct args |
| `handleSubmit sets result on success` | `result` set to API response |
| `handleSubmit sets error on failure` | `error` set when API throws |
| `handleSubmit loading state` | `loading` true during call, false after |
| `handleClear resets all state` | text, result, nextTimes, error all cleared |
| `handleSubmit skips empty text` | API not called for whitespace-only input |

### Component Tests

| Component | Tests |
|-----------|-------|
| **InputCard** | Renders textarea with placeholder; calls onChange on input; calls onSubmit on Enter; shows spinner when loading; disables button when loading or empty |
| **ResultCard** | Shows cron, explanation, next times; shows warning badge when `result.warning` is set; calls onClear on button click |
| **ErrorCard** | Shows error message; calls onRetry on button click |
| **CronBadge** | Shows cron text; copies to clipboard on click; shows "Copied!" feedback |

### API Client Tests — `api/cron.test.ts`

Mock `fetch` with `vi.fn()`.

| Test | What it covers |
|------|----------------|
| `translate constructs correct URL` | POSTs to `/api/translate` with JSON body |
| `validate constructs correct URL` | POSTs to `/api/validate` with JSON body |
| `translate returns parsed JSON` | Response correctly typed |
| `non-ok status throws error` | `detail` from JSON body used as error message |
| `non-ok with no body` | Falls back to "Request failed" |

---

## CI Integration

```yaml
# .github/workflows/test.yml (example)
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - run: pip install -e ".[test]"
      - run: python -m pytest tests/ -v --tb=short

  frontend:
    runs-on: ubuntu-latest
    steps:
      - run: npm ci
      - run: npm test
```
