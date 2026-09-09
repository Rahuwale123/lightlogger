# lightlogger — status (Phase 3 of 7)

What exists right now: a real dark-theme dashboard page that polls `/api/logs` every 2 seconds and renders live rows. First time the product is actually watchable end-to-end (with a 2s delay — SSE removes that in Phase 4).

## What actually works today

- `static/index.html` is a real, self-contained dark-theme page: fetches `/api/logs` every 2s, renders `time | LEVEL | message` rows (grey/blue/yellow/red for debug/info/warn/error), auto-scrolls to bottom as new rows arrive
- Confirmed **zero external URLs** anywhere in the file (`grep -i http` and CDN/script/link greps both return no matches) — fully offline-capable, vanilla JS, no build step
- Polling is correctness-checked against a real gotcha: `/api/logs` is a bounded ring buffer, so once it's full its length never grows again even as content keeps rotating. A naive "did the array length change" poll would silently freeze forever past that point. The JS instead tracks the last-rendered record by value and appends only what's new since it, falling back to a full re-render if the backlog rotated past what it last saw
- Statelessness verified at the HTTP level: two independent, cookie-free `GET /api/logs` calls return identical backlogs; zero `cookie`/`session`/`localStorage` anywhere in the code — a closed-and-reopened tab just sees the buffer again, no client or server state involved
- `lightlogger.start(max_logs=N)` is now wired for real: `LogBuffer.set_maxlen()` rebuilds the deque in place (preserving the object identity, keeping newest records on shrink, all records on grow). Verified end-to-end: `start(max_logs=100)` + flooding 500 logs → `/api/logs` returns exactly the newest 100
- 27 tests passing (was 23), `ruff check`, `ruff format --check`, and `mypy --strict` all clean

## What's deliberately not wired up yet

- `capture_logging`, `open_browser` params on `start()` are still accepted but inert — Phase 5 and unscoped respectively
- No pause/search/filter/expand/clear/download controls in the UI yet — Phase 6. Deliberately "ugly is fine, working matters" for this phase
- `/api/stream` (SSE) and `/api/clear` still don't exist — Phase 4 removes the 2s polling delay

## What's set up around the code

- **Layout:** `src/lightlogger/` (src-layout, Hatchling build backend); `buffer.py`, `server.py`, and now `static/index.html` all have real logic; `handler.py`/`sse.py` are still stubs
- **CI** (`.github/workflows/ci.yml`): runs the same lint/type/test gate on Python 3.9–3.13 on every push/PR
- **Publish** (`.github/workflows/publish.yml`): builds + publishes to PyPI via Trusted Publishing (OIDC) when a GitHub Release is cut — no API token stored anywhere
- **Docs:** MIT LICENSE, CHANGELOG (Keep a Changelog format), CONTRIBUTING.md, a placeholder README (real one written at Phase 7 with the demo GIF)
- **Repo:** pushed to `https://github.com/Rahuwale123/lightlogger` (private)

## Naming note

Original name `lightlog` was already taken on PyPI (an unrelated C++-backed logging lib), so the project is branded `lightlogger` everywhere — import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, but that's just the workspace name and doesn't affect the package.

## Not built yet

Live SSE streaming wired into the server (Phase 4), stdlib `logging` capture (Phase 5), UI polish — search/filter/pause/export (Phase 6), and the real coverage target + README + PyPI publish (Phase 7).

_Update this file at the end of each phase._
