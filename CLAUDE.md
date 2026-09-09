# CLAUDE.md — Developer Brief for "lightlogger"

You (Claude Code) are the developer of this project. The owner is a solo student developer building this part-time. Follow this brief exactly. When in doubt, choose the simpler option.

> **Naming note:** the product was originally conceived as "lightlog" but that name is taken on PyPI. The distribution/import name is **`lightlogger`** everywhere below (PyPI verified free on 2026-09-09).

> **Scope amendment (post-Phase 6, 2026-09-09):** log grouping (`lightlogger.group(name)`) was added to the frozen v1 API as **Phase 6.5**, before Phase 7. This is a deliberate exception to golden rule "exactly this, nothing more" — the owner evaluated it as a real differentiator (no competing zero-dep local dashboard has nested log grouping) rather than scope creep, and chose to formalize it here rather than build it as an undocumented add-on. See the new API entry in section 5, the amended record structure in section 3, section 6.5, and Phase 6.5 in section 7.

---

## 1. WHAT WE ARE BUILDING

**lightlogger** — a zero-dependency Python library that gives developers a live web dashboard for their application logs.

Developer experience (this is sacred, never break it):

```python
pip install lightlogger
```

```python
import lightlogger
lightlogger.start()          # UI now live at http://127.0.0.1:4356
lightlogger.info("user logged in")
lightlogger.error("payment failed", data={"order_id": 123})
lightlogger.var("cart", cart_dict)   # expandable JSON in UI
```

Two lines to a live, beautiful, dark-theme log dashboard in the browser. Zero config. Zero third-party dependencies. That is the entire product.

**Why this wins (from competitive research):** No existing package does "import → background thread → live localhost web UI, zero config, zero deps." Logdy is a Go binary, Chronologer needs a separate server, cutelog needs PyQt, Logfire is closed-source cloud, lnav/klp are terminal-only, Django/Flask debug toolbars are framework-locked. Our moat = developer experience + zero dependencies + in-process capture.

---

## 2. GOLDEN RULES (NEVER VIOLATE)

1. **ZERO third-party dependencies.** Python standard library ONLY. `dependencies = []` in pyproject.toml stays empty forever. If you ever feel you need a package — you don't; find the stdlib way.
2. **Bind to `127.0.0.1` ONLY.** Never `0.0.0.0`. LAN exposure must be an explicit opt-in parameter (`host="0.0.0.0"`) that prints a loud warning when used. Logs are sensitive data.
3. **Bounded memory.** All logs live in `collections.deque(maxlen=5000)` (configurable). The tool must NEVER be the reason a user's app runs out of RAM.
4. **Never block the user's app.** Server runs in a daemon thread. Logging calls must return in microseconds. No disk I/O in the logging hot path.
5. **Off unless started.** Nothing runs until the user calls `lightlogger.start()`. Document clearly: do not run in production.
6. **Simple > clever.** Vanilla HTML/JS/CSS in ONE file for the UI. No React, no build step, no npm anywhere in v1.

---

## 3. HARD TECHNICAL REQUIREMENTS (from research)

### Server
- Use `http.server.ThreadingHTTPServer` (NOT plain `HTTPServer` — SSE holds connections open and would block a single-threaded server).
- Subclass with `daemon_threads = True` and `allow_reuse_address = True`.
- Run `serve_forever()` inside `threading.Thread(daemon=True)`.
- Provide `lightlogger.stop()` → calls `httpd.shutdown()` + `server_close()` (needed for tests/notebooks).
- Port: default 4356. On `OSError` (port busy), auto-increment to next free port. Always print the final URL to stdout: `lightlogger UI → http://127.0.0.1:4356`.

### Live streaming (SSE, not websockets)
- Endpoint `/api/stream` responds with headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`.
- Each event: `data: <json>\n\n` (double newline is mandatory).
- Send `retry: 3000` at connection start and a heartbeat comment line (`: ping\n\n`) every ~15s.
- Fan-out pattern: each connected client gets its own `queue.Queue`. New log records get pushed to every client queue. Guard the client-queue set with `threading.Lock`.
- Browser side is simply `new EventSource('/api/stream')`.

### Ring buffer
- `collections.deque(maxlen=N)`. `append()` is atomic in CPython, but take a lock when ITERATING (serving backlog to a new client).

### Caller file/line capture — PERFORMANCE CRITICAL
- **NEVER use `inspect.stack()`** — it reads source files from disk on every call. Forbidden in the hot path.
- Use the stdlib logging approach: `sys._getframe()` / walk `frame.f_back`, read `frame.f_code.co_filename` and `frame.f_lineno`. Cheap attribute reads, no I/O.

### stdlib logging integration (killer feature — must have in v1)
- Ship `LightloggerHandler(logging.Handler)` whose `emit(record)` pushes into the buffer + SSE queues.
- `lightlogger.start(capture_logging=True)` attaches it to the root logger → user's EXISTING `logging` calls and even third-party library logs appear in the UI with zero code changes.
- Record structure (amended in Phase 6.5): `{time, level, message, data, file, line, logger_name, group_id, parent_group_id}`. `group_id`/`parent_group_id` are always-present keys (never omitted), typed `str | None` — every field defaults to `None` for code untouched by `group()`, so this is a value-level amendment, not a structural one. No `typing.NotRequired`/`typing_extensions` — that would violate zero-dependency on Python 3.9/3.10, where `NotRequired` doesn't exist in stdlib `typing`.

### Log grouping (`lightlogger.group(name)`) — Phase 6.5
- A context manager: `with lightlogger.group("process_order #123"): ...`. On enter, emits one group-marker record immediately (so even an empty group is visible); on exit, restores the previous group context. Nesting supported (a `group()` inside a `group()`).
- A group-marker record is just a normal `LogRecord` with `group_id` set to a fresh id (e.g. `uuid.uuid4().hex`) and `message` set to the group's display name. Every OTHER record (marker or plain log) gets `parent_group_id` set to whatever group directly contains it (`None` if top-level) — this is how nesting and containment are reconstructed client-side, by walking `parent_group_id` chains.
- Thread/async safety via `contextvars.ContextVar` (stdlib) holding "the current group id" — NOT a plain module global, which would leak across threads. Each thread that doesn't explicitly share context gets its own independent value; each asyncio `Task` gets its own copy at creation. This is what makes concurrent, non-interleaving grouping possible without extra locking.
- Group-marker records stream over `/api/stream` and appear in `/api/logs` exactly like any other record — no special-casing needed in `buffer.py`/`server.py`, since `LogBuffer.add()` already treats every record uniformly.

### Packaging the UI
- One file: `src/lightlogger/static/index.html` (HTML + CSS + JS inline).
- Read it at runtime with `importlib.resources.files("lightlogger") / "static" / "index.html"` — NEVER build paths from `__file__`.

---

## 4. FOLDER STRUCTURE (create exactly this — src layout)

```
lightlog/                        # workspace/repo root (kept as-is on disk)
├── src/
│   └── lightlogger/              # actual PyPI distribution + import name
│       ├── __init__.py          # public API: start, stop, info, warn, error, debug, var, request
│       ├── server.py            # ThreadingHTTPServer + daemon thread + routes
│       ├── handler.py           # LightloggerHandler (logging.Handler subclass)
│       ├── buffer.py            # ring buffer + SSE client fan-out
│       ├── sse.py               # SSE framing helpers
│       ├── py.typed             # empty PEP 561 marker
│       └── static/
│           └── index.html       # entire UI, single file
├── tests/
│   ├── test_buffer.py
│   ├── test_handler.py
│   └── test_server.py
├── .github/workflows/
│   ├── ci.yml                   # ruff + pytest, matrix Python 3.9–3.13
│   └── publish.yml              # PyPI Trusted Publishing on GitHub Release
├── assets/
│   └── demo.gif                 # README demo (added later)
├── pyproject.toml               # PEP 621
├── README.md
├── CHANGELOG.md                 # Keep a Changelog format
├── CONTRIBUTING.md
├── LICENSE                      # MIT
├── .pre-commit-config.yaml      # ruff lint + format
└── .gitignore
```

### pyproject.toml requirements
- Build backend: **Hatchling** (auto-detects src layout, includes package data).
- `[project]`: name `lightlogger`, version `0.1.0`, `requires-python = ">=3.9"`, description, readme, MIT license, classifiers, urls.
- `dependencies = []` — EMPTY, forever.
- `[project.optional-dependencies] dev = ["pytest", "ruff", "mypy"]`.
- Tool configs in same file: `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.mypy]` (strict).
- Semantic Versioning. Full type hints everywhere + `py.typed`.

### Publishing
- PyPI **Trusted Publishing (OIDC)** via `pypa/gh-action-pypi-publish` with `permissions: id-token: write`. **NEVER store a long-lived PyPI API token as a GitHub secret** (this exact mistake caused the LiteLLM supply-chain attack, March 2026).
- Name "lightlogger" confirmed free on PyPI (checked 2026-09-09).

---

## 5. PUBLIC API (v1 — exactly this, nothing more)

```python
lightlogger.start(port=4356, host="127.0.0.1", max_logs=5000, capture_logging=True, open_browser=False)
lightlogger.stop()
lightlogger.debug(msg, data=None)
lightlogger.info(msg, data=None)
lightlogger.warn(msg, data=None)
lightlogger.error(msg, data=None)
lightlogger.var(name, value)                          # logs any variable as expandable JSON
lightlogger.request(method, url, status, duration_ms) # API/request logging
lightlogger.group(name)                               # context manager; nested groups supported (Phase 6.5)
```

HTTP routes: `/` (UI), `/api/logs` (JSON backlog), `/api/stream` (SSE), `/api/clear` (POST, clears buffer).

`data`/`value` serialization: `json.dumps(..., default=str)` so any object works without crashing.

---

## 6. UI REQUIREMENTS (single index.html)

Must have in v1: dark theme (default), color-coded levels (debug grey, info blue, warn yellow, error red), live auto-scroll with **pause** button, **clear logs** button (calls /api/clear), search box (client-side filter), level filter dropdown, click row → expand full details (file:line, logger, pretty JSON data), download logs as .json button, connection status dot (connected/reconnecting), log counter.

Style: clean, modern, monospace font for messages, subtle borders, feels like a premium dev tool. No external fonts/CDNs (zero network deps — must work offline).

## 6.5. UI REQUIREMENTS — log grouping (Phase 6.5)

- A group-marker record renders as a collapsible header row, not a normal log line: chevron/dropdown icon (inline SVG, no icon fonts, no CDN — same offline constraint as everything else), group name, child count, and a "worst-level" hint (e.g. a red tint/badge if any descendant is `error`-level) — computed client-side by walking descendants, no new server logic needed.
- Nested groups indent their children (mirrors the browser DevTools `console.group`/`console.groupEnd` UX — a familiar reference point, not an arbitrary accordion pattern). Chevron rotates on toggle — this is user-triggered motion answering a click, not ambient decoration, so it's fine alongside the existing single ambient motion moment (the reconnecting-dot pulse from Phase 6).
- Collapsed by default. Toolbar gains expand-all / collapse-all buttons.
- Search/filter must work across grouped records: a match on a nested record auto-expands its ancestor chain so the match is visible; a group the user manually expanded/collapsed keeps that state once the search is cleared (search-driven expansion doesn't overwrite a person's own manual choice).
- Visual theme gets richer/more colorful for this phase specifically — level colors (debug/info/warn/error) stay meaningful and unchanged, but group-related chrome (headers, chevrons, badges) can use more vivid accents than Phase 6's restrained palette, as a deliberate one-time exception to "keep it restrained."
- Still one file, no CDN, fully offline, zero third-party dependencies.

---

## 7. BUILD PHASES (do IN ORDER, one phase per session, test before moving on)

- **Phase 0:** Scaffold repo (structure above), pyproject.toml, LICENSE, ruff, pre-commit, empty CI. Verify `pip install -e .` works.
- **Phase 1:** buffer.py + logger functions writing to deque. Unit tests. No server yet.
- **Phase 2:** server.py — daemon thread, `/api/logs` returns JSON. Milestone: see JSON in browser.
- **Phase 3:** Basic index.html — polls `/api/logs` every 2s, renders list. Ugly is fine.
- **Phase 4:** SSE — `/api/stream`, EventSource, live updates, heartbeat, reconnect. Remove polling.
- **Phase 5:** LightloggerHandler + `capture_logging` + file/line capture via `sys._getframe`.
- **Phase 6:** Full UI polish — search, filters, pause, clear, expand, download, status dot.
- **Phase 6.5:** Log grouping — `lightlogger.group(name)` context manager (contextvars-based, thread/async-safe, nested), amended record structure, UI collapsible group rows with expand/collapse-all and search-aware auto-expand. Scope amendment, see note at top of this file.
- **Phase 7:** Tests to ~80% coverage, CI green on 3.9–3.13, mypy strict passes, README + demo GIF, publish 0.1.0 via Trusted Publishing.

---

## 8. DO NOT (explicit bans for v1)

- ❌ NO third-party packages (not even in tests beyond pytest/ruff/mypy as dev deps)
- ❌ NO websockets (SSE only), NO React/Vue/build tools/npm, NO CDN links in the UI
- ❌ NO database, NO writing logs to disk
- ❌ NO `inspect.stack()` in the logging path
- ❌ NO `0.0.0.0` default binding
- ❌ NO multiple layouts, NO AI features, NO auth/login, NO Flask/Django/FastAPI middleware, NO Node.js port — these are ALL post-v1. If tempted, add a note to CHANGELOG "Unreleased/Ideas" instead of building.
- ❌ NO flat layout — src layout only
- ❌ NO committing secrets/tokens ever

---

## 9. README (write at Phase 7 — it's our landing page)

Order: name + one-liner → badges (PyPI, CI, license, Python versions) → **demo GIF** (before any scrolling — the single biggest factor for stars) → install + 2-line quickstart within first 200 words → features table → "Why lightlogger" (problem story) → contributing invite → MIT.

One-liner: "Live web dashboard for your Python logs — pip install, add one line, open localhost:4356. Zero dependencies."

Length 500–1500 words. GIF: <15s, ~640px, <8MB, stored in /assets. Add a security note: localhost-only by default, not for production.

---

## 10. DEFINITION OF DONE (v1)

- [ ] `pip install lightlogger` + 2 lines → working live UI
- [ ] Zero runtime dependencies (verify: fresh venv, install, run)
- [ ] Existing `logging` calls appear in UI automatically
- [ ] RAM bounded (deque maxlen honored under log flood)
- [ ] Binds 127.0.0.1 only by default; warning on override
- [ ] Search/filter/pause/clear/expand/download all work
- [ ] `lightlogger.group()` nests correctly and stays isolated across concurrent threads
- [ ] Survives: port conflict, browser refresh, SSE reconnect, `stop()` + `start()` again
- [ ] Tests pass 3.9–3.13, mypy strict clean, ruff clean
- [ ] README with GIF, CHANGELOG, published on PyPI via Trusted Publishing

Owner's context: this project is also his portfolio piece for LinkedIn/recruiters — so code quality, comments, commit messages, and docs must look professional throughout. Write commit messages in conventional style (`feat:`, `fix:`, `docs:`).
