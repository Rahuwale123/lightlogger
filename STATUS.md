# lightlogger — status (Phase 2 of 7)

What exists right now: a real, running HTTP server. `lightlogger.start()` binds a live `ThreadingHTTPServer` and `/api/logs` returns real JSON — the first genuinely visible milestone. UI is still a placeholder page; live streaming isn't wired in yet.

## What actually works today

- `lightlogger.start()` binds `127.0.0.1:4356` by default (auto-incrementing to the next free port on conflict), runs the server in a daemon thread, and prints `lightlogger UI → http://127.0.0.1:<port>`
- `lightlogger.stop()` calls `shutdown()` + `server_close()` — the port is actually freed, confirmed by re-binding it with a raw socket right after stop
- `GET /api/logs` returns the live ring buffer as JSON (`json.dumps(..., default=str)`, so arbitrary `data` objects never crash serialization); `GET /` serves the (still placeholder) `static/index.html`; anything else 404s
- Binding is `127.0.0.1`-only by default; passing `host="0.0.0.0"` prints a loud warning before binding — verified in code (grep) and by triggering the warning path directly
- Restart safety verified: `start()` → `stop()` → `start()` again in the same process works cleanly, no hang, no "address already in use"
- Port auto-increment verified with two real, separate, concurrently-running processes: process A holds `4356`, process B auto-picks `4357`, each independently serves its own logs over real HTTP — no crash, no collision
- `start()` is idempotent while already running (a no-op, not an error) — a judgment call not explicitly specified in the brief, covered by its own test
- 23 tests passing (was 17), `ruff check`, `ruff format --check`, and `mypy --strict` all clean

## What's deliberately not wired up yet

- `max_logs`, `capture_logging`, `open_browser` params on `start()` are accepted (matching the public API signature) but not yet connected to anything — `max_logs` needs the Phase 1 buffer touched again, `capture_logging`/`LightloggerHandler` is Phase 5, `open_browser` has no assigned phase yet. Not forgotten, just sequenced.
- `/api/stream` (SSE) and `/api/clear` are not built yet — Phase 4 and later. `/` and `/api/logs` only, per this phase's scope.

## What's set up around the code

- **Layout:** `src/lightlogger/` (src-layout, Hatchling build backend); `buffer.py` and `server.py` now have real logic, `handler.py`/`sse.py` are still stubs, plus a placeholder `static/index.html`
- **CI** (`.github/workflows/ci.yml`): runs the same lint/type/test gate on Python 3.9–3.13 on every push/PR
- **Publish** (`.github/workflows/publish.yml`): builds + publishes to PyPI via Trusted Publishing (OIDC) when a GitHub Release is cut — no API token stored anywhere
- **Docs:** MIT LICENSE, CHANGELOG (Keep a Changelog format), CONTRIBUTING.md, a placeholder README (real one written at Phase 7 with the demo GIF)
- **Repo:** pushed to `https://github.com/Rahuwale123/lightlogger` (private)

## Naming note

Original name `lightlog` was already taken on PyPI (an unrelated C++-backed logging lib), so the project is branded `lightlogger` everywhere — import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, but that's just the workspace name and doesn't affect the package.

## Not built yet

The polling UI (Phase 3), live SSE streaming wired into the server (Phase 4), stdlib `logging` capture (Phase 5), UI polish — search/filter/pause/export (Phase 6), and the real coverage target + README + PyPI publish (Phase 7).

_Update this file at the end of each phase._
