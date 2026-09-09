# lightlogger — status (Phase 1 of 7)

What exists right now: real in-memory logging (buffer + the six public logging functions), on top of the Phase 0 packaging/tooling skeleton. Still no HTTP server or UI — those come in Phase 2+.

## What actually works today

- `debug()`, `info()`, `warn()`, `error()`, `var()`, `request()` all write real records into a bounded in-memory ring buffer — no more `NotImplementedError` on these six
- Each record captures `{time, level, message, data, file, line, logger_name}`; file/line come from `sys._getframe` (never `inspect.stack()`, which would read source off disk on every call)
- Ring buffer (`collections.deque(maxlen=5000)`) is verified bounded under load: flooding it with 20,000 log calls leaves exactly the most recent 5,000
- Hot path measured at **~1.6 microseconds/call** (50,000 calls in 0.08s) — comfortably inside the "must return in microseconds" rule
- SSE fan-out primitives (`subscribe`/`unsubscribe`/broadcast on `LogBuffer`) are built and unit-tested now, even though nothing consumes them until Phase 4's `/api/stream` — they're pure in-memory `queue.Queue` plumbing, easy to test in isolation without a server
- `start()` / `stop()` still `raise NotImplementedError` — no server yet, so nothing is network-reachable
- 17 tests passing (was 3 placeholders), `ruff check`, `ruff format --check`, and `mypy --strict` all clean

## What's set up around the code

- **Layout:** `src/lightlogger/` (src-layout, Hatchling build backend); `buffer.py` now has real logic, `server.py`/`handler.py`/`sse.py` are still stubs, plus a placeholder `static/index.html`
- **CI** (`.github/workflows/ci.yml`): runs the same lint/type/test gate on Python 3.9–3.13 on every push/PR
- **Publish** (`.github/workflows/publish.yml`): builds + publishes to PyPI via Trusted Publishing (OIDC) when a GitHub Release is cut — no API token stored anywhere
- **Docs:** MIT LICENSE, CHANGELOG (Keep a Changelog format), CONTRIBUTING.md, a placeholder README (real one written at Phase 7 with the demo GIF)
- **Repo:** pushed to `https://github.com/Rahuwale123/lightlogger` (private)

## Naming note

Original name `lightlog` was already taken on PyPI (an unrelated C++-backed logging lib), so the project is branded `lightlogger` everywhere — import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, but that's just the workspace name and doesn't affect the package.

## Not built yet

The HTTP server (Phase 2), the polling UI (Phase 3), live SSE streaming wired into a real server (Phase 4), stdlib `logging` capture (Phase 5), UI polish — search/filter/pause/export (Phase 6), and the real coverage target + README + PyPI publish (Phase 7).

_Update this file at the end of each phase._
