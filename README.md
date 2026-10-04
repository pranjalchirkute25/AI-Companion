# Blind Spot

**See what your thinking might be missing.**

Blind Spot is an AI powered decision workspace. It helps people examine assumptions, evidence, options, and open questions while leaving the decision with the person making it.

## The problem

People can give extra weight to the first or most visible factors in a decision. Blind Spot is designed to make less visible questions easier to examine without issuing a recommendation or ranking options.

## Approach and features

- **Decision canvas:** describe the decision, what matters, options, and constraints or timing.
- **Structured analysis:** the server requests focused factors, possible assumptions, overlooked considerations, a counter perspective, and reflective questions.
- **Blind Spot Radar:** shows exploration states for evidence, assumptions, alternatives, stakeholders, risks and consequences, and reversibility. Each state includes its reason; states are not decision scores.
- **Adaptive reflection:** the workspace presents one question at a time. After an answer, the server requests a focused follow up; only the first returned question is shown.
- **Decision brief:** compiles the original description, analysis, answers, and the user’s reflection into a working summary. It labels unverified information and ends with “YOU DECIDE”.
- **Safe rendering:** user and model text is inserted with DOM text nodes rather than interpreted as HTML.

The radar uses the initial request and analysis to describe what has been surfaced so far. It is a prompt for exploration, not a measure of decision quality. Blind Spot does not verify claims or research external facts.

## How the Blind Spot concept works

The AI receives the decision details as passive user data, then returns structured JSON for a neutral analysis. A server-side validator checks generated text for verdict language. If generation fails or fails validation, a neutral fallback is returned. The fallback does not attribute invented assumptions or blind spots to the user; it makes the outage clear and offers general reflection questions.

The interface treats AI inferences as possibilities. The user remains responsible for evaluating their fit, gathering evidence, and making the decision.

## Architecture

```text
Browser (semantic HTML, CSS, vanilla JavaScript)
        │ same-origin JSON requests
        ▼
FastAPI application
  ├── Pydantic request and response schemas
  ├── analysis and follow-up routes
  ├── Gemini service with timeout, retries, and response validation
  ├── verdict-language validator and neutral fallback
  └── in-memory session history and TTL cache
        │
        └── Google Gemini API (optional; GEMINI_API_KEY)
```

### Technology

- Python 3.12+
- FastAPI, Pydantic Settings
- Google GenAI Python SDK (optional at runtime)
- Static HTML, CSS, and vanilla JavaScript
- Pytest, pytest-asyncio, HTTPX, and Ruff for development checks
- Docker image intended for Google Cloud Run

## Security and privacy considerations

- Gemini credentials are read from server environment variables and are not sent to the browser.
- API inputs have length constraints and are sanitized before prompt construction.
- User-provided text is treated as data in the model prompt; generated output is checked for recommendation language.
- Response headers include a content security policy and other browser security headers.
- API calls are rate limited per process and IP.
- Sessions and cache entries are held in process memory with expiration. There is no login, database, or durable storage. Do not enter highly sensitive personal information.
- The in-memory rate limiter and session store are process local. Multi-worker or horizontally scaled deployments can route a follow-up to a process without its original session. Use a single worker/instance for a coherent demo, or replace these stores with shared, appropriately protected storage before scaling.

These controls reduce risk but do not guarantee security or confidentiality. Review deployment access, logging, retention, and provider terms before using real personal data.

## Local setup

Requires Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set GEMINI_API_KEY in .env for live model analysis. It may be left unset for the neutral offline fallback.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). API documentation is available at `/api/docs` only when `DEBUG=true`. The health route is `/api/health`.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Server-side Google Gemini API key | unset |
| `GEMINI_MODEL` | Gemini model identifier | `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Per-attempt generation timeout | `30` |
| `GEMINI_MAX_RETRIES` | Maximum generation attempts | `3` |
| `PORT` | HTTP server port (Cloud Run supplies this) | `8000` |
| `DEBUG` | Enables local API docs and development CORS behavior | `false` |
| `RATE_LIMIT_PER_MINUTE` | Per-process request limit | `20` |
| `CACHE_TTL_SECONDS` | Analysis cache lifetime | `3600` |
| `MAX_SESSION_HISTORY` | Reflection history cap | `10` |
| `SESSION_TTL_SECONDS` | In-memory session lifetime | `86400` |

Never commit `.env` or credentials. `.env.example` contains placeholders only.

## Tests and development checks

Run the test suite and lint checks from the project root:

```powershell
python -m pytest -q
ruff check app tests
```

Tests cover schemas, endpoint behavior, session flow, response validation, fallback behavior, and security headers. Live Gemini behavior requires a valid API key and network access; tests should mock external model calls.

## Docker and Cloud Run

Build and run locally:

```powershell
docker build -t blind-spot .
docker run --rm -p 8000:8000 -e PORT=8000 -e GEMINI_API_KEY=your_key blind-spot
```

For Cloud Run, build and push the image to Artifact Registry, then deploy the image with `PORT` supplied by Cloud Run and `GEMINI_API_KEY` stored as a Secret Manager secret. The Dockerfile starts one Uvicorn worker. Configure a single Cloud Run instance while sessions are process-local, or move session/rate-limit state to a shared store before scaling. Verify the deployed URL and health route in a fresh browser session. No deployment has been performed from this workspace.

## Limitations and future improvements

- No authentication or durable user-owned sessions.
- AI outputs may be incomplete, generic, or mistaken; external facts are not checked.
- Radar states are heuristic summaries of what was mentioned and what the model returned, not an evaluated psychological or decision score.
- Pre-mortem, detailed stakeholder mapping, and consequence chains currently appear as reflection prompts rather than separately validated model outputs.
- The in-memory session model is unsuitable for multi-process scaling without shared state.

Possible next steps include explicit fact/belief/assumption/prediction labels, validated structured pre-mortem and consequence outputs, a more complete evidence and stakeholder model, browser accessibility review, and shared session storage if persistence is needed.

## License

No license has been specified yet.
