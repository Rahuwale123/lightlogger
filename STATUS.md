# lightlogger — status (Phase 5 of 7)

What exists right now: the "zero code changes" killer feature. Existing `logging` calls — the user's own and third-party libraries' — now show up in the dashboard automatically once `lightlogger.start()` is called, no code changes required.

## What actually works today

- `LightloggerHandler(logging.Handler)` converts stdlib `logging.LogRecord`s into our record shape (`record.pathname`/`.lineno`/`.name`/`.getMessage()`/`.created`) and pushes into the same `LogBuffer.add()` used everywhere else — which already covers both the ring buffer and SSE fan-out, no separate broadcast code needed. Level mapping: DEBUG→debug, INFO→info, WARNING→warn, ERROR/CRITICAL→error (only 4 UI colors exist)
- `emit()` wraps its body in `try/except Exception: self.handleError(record)`, matching the stdlib's own handler convention — a bug in our handler can never crash or disrupt the user's actual logging calls
- `start(capture_logging=True)` (the default) attaches a fresh `LightloggerHandler` to the root logger; `stop()` detaches exactly that instance. Verified end-to-end: `start()` → `stop()` → `start()` attaches exactly one handler each time, never two, and a probe log line appears exactly once after the second `start()`, not twice
- **Deliberate design decision, verified working**: the library never calls `.setLevel()` on the root logger. Forcing the level open (e.g. to `DEBUG`) so `.info()` calls would appear was tempting, but that's a global side effect that would also unmute the user's *other* existing handlers (console, file, etc.) — more disruptive than "zero code changes" should mean. Confirmed by direct test: with the root logger at its default `WARNING`, `.info()` is correctly **not** captured, while `.warning()` is — we mirror what the user's app already emits, we don't silently unlock everything
- Side task done: heartbeat interval is now a `create_server(..., heartbeat_interval=...)` parameter (internal only — **not** added to `lightlogger.start()`, which keeps the frozen public API exactly as specified). Production still defaults to the real 15s; the heartbeat test now builds its own throwaway server at `heartbeat_interval=0.2` instead of waiting the real interval
- That speedup surfaced a genuine test-isolation gap from Phase 4: several `/api/stream` tests closed their connection without waiting for the server to notice and unsubscribe, and the old 15s heartbeat test's real sleep had been incidentally giving those stragglers time to clean up before the leak-detection test measured its baseline. Fixed by force-clearing the subscriber set between tests. This did **not** indicate a real production leak — the dedicated leak-detection test (which nudges log calls and polls for cleanup) still passes unchanged and validates the actual mechanism; this was purely tests not waiting for their own cleanup to finish
- 34 tests passing (was 32), full suite now ~9s (down from ~22s — the heartbeat speedup was the dominant cost), confirmed stable across multiple independent full-suite runs. `ruff check`, `ruff format --check`, and `mypy --strict` all clean

## What's deliberately not wired up yet

- `open_browser` param on `start()` is still accepted but inert — no phase has claimed it yet
- No pause/search/filter/expand/clear/download controls in the UI yet — Phase 6. Still "ugly is fine, working matters"
- `/api/clear` doesn't exist yet
- `stop()` doesn't proactively close in-flight SSE connections — unchanged from Phase 4, not a correctness issue

## What's set up around the code

- **Layout:** `src/lightlogger/` (src-layout, Hatchling build backend) — every module now has real logic: `buffer.py`, `server.py`, `sse.py`, `handler.py`, `static/index.html`
- **CI** (`.github/workflows/ci.yml`): runs the same lint/type/test gate on Python 3.9–3.13 on every push/PR
- **Publish** (`.github/workflows/publish.yml`): builds + publishes to PyPI via Trusted Publishing (OIDC) when a GitHub Release is cut — no API token stored anywhere
- **Docs:** MIT LICENSE, CHANGELOG (Keep a Changelog format), CONTRIBUTING.md, a placeholder README (real one written at Phase 7 with the demo GIF)
- **Repo:** pushed to `https://github.com/Rahuwale123/lightlogger` (private)

## Naming note

Original name `lightlog` was already taken on PyPI (an unrelated C++-backed logging lib), so the project is branded `lightlogger` everywhere — import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, but that's just the workspace name and doesn't affect the package.

## Not built yet

UI polish — search/filter/pause/export (Phase 6), and the real coverage target + README + PyPI publish (Phase 7).

_Update this file at the end of each phase._
