# lightlogger — status (Phase 4 of 7)

What exists right now: real live streaming. The 2-second polling delay is gone — logs now push to the browser over Server-Sent Events the instant they're written, with a connection status dot and auto-reconnect.

## What actually works today

- `GET /api/stream` is a real SSE endpoint: `text/event-stream` + `Cache-Control: no-cache` headers, `retry: 3000` sent first, each record framed as `data: <json>` with the mandatory blank-line terminator, and a `: ping` heartbeat comment every 15s so idle connections don't look dead. Wire format verified byte-for-byte with a raw `urllib` read — not just "the browser seemed to work"
- Per-client fan-out reuses Phase 1's `LogBuffer.subscribe()`/`unsubscribe()` unchanged — each `/api/stream` connection gets its own `queue.Queue`, blocking on it with a 15s timeout that doubles as the heartbeat trigger
- **Subscriber leak prevention verified, not assumed**: closing a stream connection is detected the standard way (the next `wfile.write()` fails with `BrokenPipeError`/`ConnectionResetError`), `finally: unsubscribe()` always runs, and a test proves the subscriber count returns to exactly its prior value after disconnect — this matters because a leaked queue per dropped tab would silently violate the bounded-memory golden rule over a long-running app
- UI now uses `new EventSource('/api/stream')` instead of the 2s poll: `onopen` → green dot + one `/api/logs` backlog refresh (covers both first load and every reconnect with the same code path), `onmessage` → append the row live, `onerror` → red dot
- **Reconnect fully verified in a real browser** (Playwright, at my own initiative per the owner's explicit go-ahead this round — not the default for this project): killed the server mid-session, watched the dot go red, brought the server back up, watched the dot go green again and the page cleanly re-render (no duplicates, no stale rows) once it detected the backlog had rotated past what it last knew
- Judgment call: added a `handle_error()` override on `LightloggerServer` that swallows `BrokenPipeError`/`ConnectionResetError` instead of dumping a traceback — without it, a closed SSE tab spams the host app's stderr on every disconnect. Same spirit as the existing quiet `log_message()` override
- 32 tests passing (was 27), `ruff check`, `ruff format --check`, and `mypy --strict` all clean. One of those tests genuinely waits the real 15s heartbeat interval (no test-only shortcut used, to keep the real behavior honest) — it's why the suite now takes ~22s instead of ~5s

## What's deliberately not wired up yet

- `capture_logging`, `open_browser` params on `start()` are still accepted but inert — Phase 5 and unscoped respectively
- No pause/search/filter/expand/clear/download controls in the UI yet — Phase 6. Still "ugly is fine, working matters"
- `/api/clear` doesn't exist yet
- `stop()` doesn't proactively close in-flight SSE connections — their daemon threads unblock and clean themselves up on their next queue timeout/write attempt, same disconnect-detection path as a browser tab closing. Not a correctness bug (verified: `stop()` → `start()` still works cleanly), just means a stopped server's stream threads linger briefly rather than closing instantly

## What's set up around the code

- **Layout:** `src/lightlogger/` (src-layout, Hatchling build backend); `buffer.py`, `server.py`, `sse.py`, and `static/index.html` all have real logic now; only `handler.py` (Phase 5) is still a stub
- **CI** (`.github/workflows/ci.yml`): runs the same lint/type/test gate on Python 3.9–3.13 on every push/PR
- **Publish** (`.github/workflows/publish.yml`): builds + publishes to PyPI via Trusted Publishing (OIDC) when a GitHub Release is cut — no API token stored anywhere
- **Docs:** MIT LICENSE, CHANGELOG (Keep a Changelog format), CONTRIBUTING.md, a placeholder README (real one written at Phase 7 with the demo GIF)
- **Repo:** pushed to `https://github.com/Rahuwale123/lightlogger` (private)

## Naming note

Original name `lightlog` was already taken on PyPI (an unrelated C++-backed logging lib), so the project is branded `lightlogger` everywhere — import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, but that's just the workspace name and doesn't affect the package.

## Not built yet

stdlib `logging` capture (Phase 5), UI polish — search/filter/pause/export (Phase 6), and the real coverage target + README + PyPI publish (Phase 7).

_Update this file at the end of each phase._
