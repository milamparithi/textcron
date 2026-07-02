# TextCron — Natural Language to Cron Schedule

Convert plain English schedule descriptions into valid cron expressions using a provider-agnostic LLM, with Langfuse observability, guardrails, and evals.

---

## 1. Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          Docker Compose                                    │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────┐       │
│  │   Frontend   │   │   Backend    │   │ Langfuse │   │ Postgres │       │
│  │  React 18    │   │  FastAPI     │   │  v2      │   │   16     │       │
│  │  Vite/Nginx  │   │  Uvicorn     │   │          │   │          │       │
│  │              │   │              │   │          │   │          │       │
│  │  port 80     │   │  port 8000   │   │ port 3000│   │          │       │
│  └──────┬───────┘   └──────┬───────┘   └─────┬────┘   └──────────┘       │
│         │     HTTP/JSON    │                  │                            │
│         ◄─────────────────►│◄────────────────┘                            │
│                            │         (ingestion API)                       │
│                            │                                              │
│                            │  ┌──────────┐                                │
│                            │  │  LLM     │  (litellm — agnostic)         │
│                            │  │          │                                │
│                            │  └──────────┘                                │
│                            │                                              │
│              Network: textcron-net                                        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend — Python FastAPI

### 2.1 Tech Stack
- **Python 3.12** (slim Docker image)
- **FastAPI** — REST framework
- **Uvicorn** — ASGI server
- **Pydantic v2** — request/response models
- **litellm** — provider-agnostic LLM client (OpenAI, Gemini, Anthropic, Groq, Ollama, Azure, etc.)
- **croniter** — cron expression validation & human-readable explanation
- **langfuse** (Python SDK) — observability via direct ingestion API (traces, generations, scores)
- **python-dotenv** — environment config

### 2.2 API Endpoints

#### `POST /api/translate`
Translate natural language to a cron expression.

**Request:**
```json
{
  "text": "every weekday at 3pm",
  "timezone": "UTC"
}
```

**Response (success):**
```json
{
  "cron": "0 15 * * 1-5",
  "text": "every weekday at 3pm",
  "explanation": "At 3:00 PM, Monday through Friday",
  "warning": "",
  "trace_id": "abc-123-def"
}
```

**Response (with frequency warning):**
```json
{
  "cron": "* * * * *",
  "text": "every minute",
  "explanation": "Every minute",
  "warning": "Schedule runs every 1 minute(s) — consider a minimum of 5 min to avoid frequent runs",
  "trace_id": "abc-123-def"
}
```

**Error (400 — input validation or LLM-detected issue):**
```json
{
  "detail": "Unable to parse schedule. Please rephrase."
}
```
```json
{
  "detail": "February never has 30 days. Please use a valid date."
}
```
```json
{
  "detail": "Ambiguous: 'every second day' could mean every 2 days or on the 2nd of every month. Please clarify."
}
```

**Error (502 — LLM output validation failure):**
```json
{
  "detail": "LLM response missing fields: minute, hour"
}
```

#### `POST /api/validate`
Validate a raw cron expression and preview next runs.

**Request:**
```json
{
  "cron": "0 15 * * 1-5"
}
```

**Response:**
```json
{
  "valid": true,
  "explanation": "Next run at 2026-07-03 15:00 UTC",
  "next_times": ["2026-07-03 15:00", "2026-07-06 15:00", "2026-07-07 15:00"]
}
```

#### `POST /api/feedback`
Submit user rating for a translation trace (requires Langfuse configured).

**Request:**
```json
{
  "trace_id": "abc-123-def",
  "rating": "positive",
  "comment": ""
}
```

**Response:**
```json
{
  "id": "abc-123-def"
}
```

**Errors:**
- `400` — Langfuse not configured, missing `trace_id`, or invalid rating value
- `400` — Comment exceeds 500 characters

### 2.3 LLM Integration — Structured JSON Output

The LLM returns a structured JSON object describing the schedule. The backend composes the final cron expression from that structure.

- **Provider-agnostic**: Uses **litellm** supporting 100+ models. Provider selected at runtime via env config.
- **`LlmResult` dataclass** returned by `translate()`:
  - `parsed` — the parsed JSON dict from LLM
  - `model` — the model name used
  - `prompt_tokens` / `completion_tokens` / `total_tokens` — token counts
  - `input_cost` / `output_cost` / `total_cost` — cost tracking
  - `prompt` — the messages sent
  - `response_text` — raw LLM response string
- **Prompt strategy**:
  - System prompt instructs the LLM to output schedule fields or an `error` field — never a raw cron string
  - **Error detection** (LLM is prompted to detect):
    - Impossible dates (e.g. "February 30")
    - Invalid intervals (e.g. "every 0 minutes")
    - Unsupported concepts (e.g. "fortnightly", "quarterly", "every other day")
    - Ambiguity (e.g. "every second day", "every morning")
  - When detected, returns `{"error": "clear message"}` instead of schedule fields
  - A few-shot examples are included in the prompt for accuracy
  - Temperature = 0 for deterministic output
- **Provider prefixes**: Auto-prefixed for litellm compatibility — `gemini` → `gemini/`, `anthropic` → `anthropic/`, `groq` → `groq/`, `openai`/`azure` → no prefix
- **Per-provider env vars**: Sets `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY` from `LLM_API_KEY` so litellm can discover them
- **Configuration** (env vars):
  - `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`

The JSON schema the LLM is asked to return (for valid schedules):

```json
{
  "minute":   "*" | int | "*/N" | "a,b,c",
  "hour":     "*" | int | "*/N" | "a,b,c",
  "day_of_month": "*" | int | "*/N" | "a,b,c",
  "month":        "*" | int | "*/N" | "a,b,c",
  "day_of_week":  "*" | int | "*/N" | "a,b,c",
  "explanation":  "human-readable description"
}
```

### 2.4 Conversion & Validation Flow

1. Receive NL text
2. Input validation (length, character allowlist, time keywords, gibberish detection)
3. Rate limiting check (30/min per IP, 100/day global)
4. Create Langfuse trace
5. Call LLM — returns `LlmResult` with `parsed` dict
6. Record LLM generation in Langfuse (model, tokens, cost, timing)
7. If LLM returned `error` → `400` with LLM's message
8. If LLM returned schedule fields → validate field values (range bounds, cron syntax pattern)
9. Compose cron from five fields `{minute} {hour} {day_of_month} {month} {day_of_week}`
10. Validate final cron with `croniter.is_valid()`
11. Compute next N occurrences + check frequency floor (warning if <5 min)
12. Return `TranslateResponse` with `trace_id`

Stage-8 failures indicate the LLM didn't follow instructions → `502 Bad Gateway` (`LlmSystemError`).

---

## 3. Frontend — React + TypeScript

### 3.1 Tech Stack
- **React 18.3** with **TypeScript**
- **Vite** — build tool (with dev proxy `/api` → `localhost:8000`)
- **Tailwind CSS v4** — utility-first styling (light theme, `@tailwindcss/vite` plugin)
- **sonner** — toast notifications

No React Query, no Zustand, no Router — plain `fetch` + React state.

### 3.2 Route Design
Single-page app with one main view:

| Route | Component | Purpose |
|-------|-----------|---------|
| `/`   | `HomePage` | Input field + results |

### 3.3 Component Tree

```
App
└── Layout
    └── HomePage
        ├── Header             — app title + tagline
        ├── InputCard          — textarea + submit button
        │   ├── TextArea       — auto-growing, Enter to submit
        │   └── SubmitBtn      — spinner when loading
        ├── ResultCard         — appears after success
        │   ├── CronBadge      — monospaced cron (copyable)
        │   ├── Warning        — amber banner for frequent schedules
        │   ├── NextTimes      — list of next scheduled times
        │   ├── FeedbackWidget — thumbs up/down (auto-submits)
        │   └── Translate another button
        └── ErrorCard          — error message + retry button
```

### 3.4 Data Flow

```
User types text
  → Enter key or click Translate
  → POST /api/translate
  → loading spinner on button
  → success → POST /api/validate (for next times)
  → display ResultCard with cron + explanation + next times + feedback
  → error → display ErrorCard with message
  → user can Translate another to reset
```

### 3.5 API Client (TypeScript)

```typescript
interface TranslateRequest  { text: string; timezone?: string }
interface TranslateResponse {
  cron: string; text: string; explanation: string;
  warning?: string; trace_id?: string;
}

interface ValidateRequest   { cron: string }
interface ValidateResponse  { valid: boolean; explanation: string; next_times: string[] }

interface FeedbackRequest   { trace_id: string; rating: "positive" | "negative"; comment?: string }
interface FeedbackResponse  { id: string }
```

### 3.6 FeedbackWidget

- Rendered in `ResultCard` when `trace_id` is present
- Two thumb buttons (👍/👎)
- Clicking a thumb immediately `POST /api/feedback` — no separate send step
- On success: shows "Thanks for your feedback!" text, buttons disabled
- Uses `sessionStorage` to prevent duplicate submissions per trace
- Error message shown inline on failure

---

## 4. UI / UX Specifications

### 4.1 Visual Style

| Property | Value |
|----------|-------|
| **Theme** | Light / white background |
| **Primary** | Gray-900 (`#111827`) for buttons/text |
| **Accent** | Amber-50/700 for warnings |
| **Border radius** | `12px` on cards, `8px` on inputs |
| **Shadow** | `shadow-sm` |
| **Typography** | System font stack (Tailwind default) |
| **Max content width** | `640px` centered |

### 4.2 Mobile Responsiveness

- Single-column layout at all breakpoints
- Full-width inputs on mobile (padding `16px`)
- CTA button stretches full width on small screens
- Touch targets minimum `44×44px`
- Font sizes `16px` minimum on inputs (prevents iOS zoom)

### 4.3 States

| State | Behaviour |
|-------|-----------|
| **Empty** | Placeholder: *"e.g. every weekday at 3pm"* |
| **Loading** | Button shows spinner, inputs disabled |
| **Success** | Fade-in animation on result card |
| **Error** | Error card with retry button |
| **Frequency warning** | Amber banner within ResultCard |

### 4.4 Accessibility

- Input labelled with `<label htmlFor>`
- Colour is never the only indicator of state
- Focus rings visible (`ring-2`)
- Keyboard navigable (Enter to submit, Tab through results)

---

## 5. Guardrails

### 5.1 Rate Limiting

| Limit | Scope | Implementation |
|-------|-------|----------------|
| **30 requests / minute** | Per IP | Sliding window in memory; cleaned on each request |
| **100 requests / day** | Global (all users) | Resets at UTC midnight; prevents cost overrun |

Both enforced via `Depends(check_rate_limit)` on `/api/translate` and `/api/feedback`. Exceeded limits return `429 Too Many Requests`.

### 5.2 Input Validation (pre-LLM)

| Check | Threshold | Rationale |
|-------|-----------|-----------|
| **Length cap** | Max 500 characters | Prevents token waste and prompt injection |
| **Character allowlist** | `a-zA-Z0-9 .,!?:;\-/@#()&'"\n` | Blocks `<`, `{`, `}`, backtick injection vectors |
| **Schedule keyword** | Must contain ≥1 time-related token | Rejects random text before LLM call |
| **Repetition detection** | Reject if any char >40% of input | Blocks `aaaa...` garbage |

### 5.3 Output Validation (post-LLM)

**Stage 1 — LLM-reported error (`400 Bad Request`)**  
LLM's `error` field passed directly to the user.

**Stage 2 — Backend enforcement (`502 Bad Gateway`)**

| Check | Detail |
|-------|--------|
| **Schema completeness** | All five cron fields + `explanation` must be present |
| **Cron field pattern** | Each field must match `^(...)\*$` regex allowing `*/N`, `N`, `N-M`, `N/M`, commas |
| **Range enforcement** | minute 0–59, hour 0–23, day_of_month 1–31, month 1–12, day_of_week 0–6 |
| **Explanation check** | Non-empty and ≤200 characters |

### 5.4 Safety Warning (not a failure)

If interval <5 minutes, a `warning` field is added to the response. The expression is still returned.

### 5.5 LLM Timeout

The `litellm.completion` call has a **15-second timeout**. Provider hangs return `502`.

---

## 6. Langfuse Observability

### 6.1 Client Architecture

`langfuse_client.py` wraps the Langfuse SDK with graceful degradation:
- **Noop mode**: If `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are missing, all calls are no-ops
- **`get_client()`**: Lazy singleton; returns `_NoopClient` if keys missing or SDK fails
- **`is_available()`**: Returns whether real client is active

### 6.2 Ingestion API (manual — no OTLP)

Langfuse v2's OTLP endpoint may return 404, so the client uses the **direct ingestion API**:

| Method | Langfuse API | What it captures |
|--------|-------------|------------------|
| `create_trace()` | `IngestionEvent_TraceCreate` | Trace ID, name, input data |
| `create_generation()` | `IngestionEvent_ObservationCreate(type=GENERATION)` | Model, tokens, cost, timing, input/output, level (ERROR for failures) |
| `score_trace()` | `lf.create_score()` (SDK convenience) | User rating (1.0 / 0.0), optional comment |

### 6.3 Tracing Flow

```
POST /api/translate
  → create_trace("translate", input={text})
  → LLM call
  → on success: create_generation(level=DEFAULT, model, tokens, cost)
  → on exception: create_generation(level=ERROR, status_message=str(e))
  → return trace_id in response

POST /api/feedback
  → score_trace(trace_id, name="user_rating", value=1.0/0.0, comment)
```

### 6.4 Feedback

- `POST /api/feedback` attaches a score to the trace in Langfuse
- `comment` omitted from kwargs when empty (passing `""` hides the score in Langfuse UI)
- `lf.flush()` called after scoring (scores processed by background consumer within ~2s)
- Returns `400` if Langfuse not configured

---

## 7. Evaluation

### 7.1 Golden Dataset

25 curated entries at `backend/tests/golden_dataset.json` covering:
- Valid schedules (various frequencies, weekdays, weekends, specific times)
- Edge cases (empty input, whitespace, too long, disallowed characters)
- LLM-detected errors (impossible dates, invalid intervals, unsupported concepts, ambiguity)
- LLM system errors (missing fields, out-of-range values, invalid cron syntax, missing explanation)

Run tests:

```bash
# Fast — uses mock LLM responses
pytest backend/tests/test_golden.py

# Real — calls configured LLM
pytest backend/tests/test_golden.py --real-llm --sample=5
```

### 7.2 LLM-as-Judge

`backend/scripts/eval_judge.py` evaluates translation quality across 4 dimensions using a separate judge LLM:

| Dimension | Scale | What it measures |
|-----------|-------|-----------------|
| `cron_correctness` | 0–5 | Does the cron expression match the described schedule? |
| `explanation_accuracy` | 0–5 | Is the explanation clear and accurate? |
| `error_handling` | 0–5 | Are invalid inputs handled correctly? |
| `safety_warnings` | 0–5 | Are frequent schedules flagged appropriately? |

```bash
python backend/scripts/eval_judge.py             # default judge model
python backend/scripts/eval_judge.py --sample 10  # subset
python backend/scripts/eval_judge.py --judge-model "anthropic/claude-sonnet-4-20250514"
```

The judge auto-falls back to the system model on rate limits and computes a programmatic pass/fail from score thresholds. JSON reports are saved to `backend/scripts/eval_results/`.

---

## 8. Project Structure

```
textcron/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, router registration
│   │   ├── api/
│   │   │   ├── translate.py        # POST /api/translate
│   │   │   ├── validate.py         # POST /api/validate
│   │   │   └── feedback.py         # POST /api/feedback
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic models
│   │   └── services/
│   │       ├── llm.py              # LLM client, prompt, LlmResult dataclass
│   │       ├── cron.py             # croniter: compose, is_valid, next_times
│   │       ├── guard.py            # rate limiting, input/output validation
│   │       └── langfuse_client.py  # Langfuse ingestion API wrapper
│   ├── tests/
│   │   ├── conftest.py             # fixtures (clear_rate_limits, client)
│   │   ├── golden_dataset.json     # 25 curated test entries
│   │   ├── test_golden.py          # parameterized golden test runner
│   │   ├── api/                    # endpoint tests
│   │   └── services/               # service unit tests
│   ├── scripts/
│   │   ├── eval_judge.py           # LLM-as-Judge evaluation runner
│   │   └── judge_prompt.py         # 4-dimension judge rubric prompt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # root component
│   │   ├── main.tsx                # Vite entry
│   │   ├── api/
│   │   │   └── cron.ts             # typed API client (fetch)
│   │   ├── types/
│   │   │   └── cron.ts             # TypeScript interfaces
│   │   ├── hooks/
│   │   │   └── useTranslate.ts     # state machine hook
│   │   ├── pages/
│   │   │   └── HomePage.tsx        # page-level component
│   │   └── components/
│   │       ├── Layout.tsx
│   │       ├── InputCard.tsx       # textarea + submit
│   │       ├── ResultCard.tsx      # cron + explanation + warning + next times + feedback
│   │       ├── ErrorCard.tsx
│   │       ├── CronBadge.tsx       # monospaced copyable cron
│   │       ├── NextTimes.tsx       # next N scheduled times
│   │       └── FeedbackWidget.tsx  # thumbs up/down
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts              # proxy /api → localhost:8000
│   ├── nginx.conf                  # reverse-proxy /api/ → backend
│   └── Dockerfile                  # multi-stage (Node build → Nginx serve)
│
├── scripts/
│   └── take_screenshots.py         # Playwright screenshot generator
│
├── spec/
│   └── README.md                   # this file
├── .env.example
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 9. Docker

### 9.1 Services

| Service | Image base | Port | Purpose |
|---------|-----------|------|---------|
| `backend` | `python:3.12-slim` | `8000` | FastAPI app (Uvicorn) |
| `frontend` | Multi-stage Node → Nginx | `80` | Static build served via Nginx |
| `langfuse` | `langfuse/langfuse:2` | `3000` | Langfuse observability dashboard |
| `postgres` | `postgres:16` | — | Langfuse database (with healthcheck + `pgdata` volume) |

### 9.2 Dockerfile — Backend

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.3 Dockerfile — Frontend (multi-stage)

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 9.4 Nginx Config

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

All `/api/*` requests are reverse-proxied to the backend; all other routes serve the SPA.

### 9.5 Docker Compose

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: [.env]
    environment:
      - LANGFUSE_HOST=http://langfuse:3000
    depends_on: [langfuse]
    networks: [textcron-net]

  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [backend]
    networks: [textcron-net]

  langfuse:
    image: langfuse/langfuse:2
    ports: ["3000:3000"]
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      - DATABASE_URL=postgresql://langfuse:langfuse@postgres:5432/langfuse
      - NEXTAUTH_SECRET=change-me-to-a-random-string
      - NEXTAUTH_URL=http://localhost:3000
      - SALT=change-me-to-another-random-string
      - LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=false
    networks: [textcron-net]

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=langfuse
      - POSTGRES_DB=langfuse
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]
      interval: 5s
      timeout: 5s
      retries: 5
    volumes: [pgdata:/var/lib/postgresql/data]
    networks: [textcron-net]

volumes: { pgdata: }
networks: { textcron-net: }
```

### 9.6 Development vs Production

| Mode | Command | Notes |
|------|---------|-------|
| **Dev (full)** | `docker compose up --build` | Builds all images and starts services |
| **Dev (frontend only)** | `npm run dev` | Vite dev server with proxy to `localhost:8000` |
| **Prod** | `docker compose up -d` | Daemonised, Nginx serves static build |

### 9.7 Environment Variables

```bash
# --- LLM (provider-agnostic) ---
LLM_PROVIDER=openai          # openai | gemini | anthropic | groq | ollama | azure | ...
LLM_API_KEY=sk-...           # API key for chosen provider
LLM_MODEL=gpt-4o-mini        # bare model name (auto-prefixed for some providers)
LLM_BASE_URL=                # optional: custom endpoint (e.g. Ollama)
LLM_TEMPERATURE=0

# --- Langfuse Observability ---
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000   # overridden to http://langfuse:3000 in Docker

# --- Langfuse Self-Hosted (docker-compose only) ---
DATABASE_URL=postgresql://langfuse:langfuse@postgres:5432/langfuse
NEXTAUTH_SECRET=change-me-to-a-random-string
NEXTAUTH_URL=http://localhost:3000
SALT=change-me-to-another-random-string
```

---

## 10. Future Considerations (out of scope for v1)

- Translation history / recently used (localStorage)
- Dark mode toggle
- i18n (multi-language NL input)
- Offline cron validation via WASM-compiled croniter
- Shareable links with pre-filled text
- Batch evaluation dashboard
