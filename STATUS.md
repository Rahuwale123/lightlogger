# lightlogger — status (Phase 6 of 7)

What exists right now: the full dashboard UI — search, level filter, pause/resume with no dropped records, clear, click-to-expand detail panels, JSON download, a real favicon, and `open_browser` wiring. This is the UI the eventual demo GIF will show.

## What actually works today

- **Search box + level filter**, both client-side, ANDed together: every row gets a `hidden` toggle based on whether it matches the current search text and level filter; new live/paused-flush rows are filtered at creation time, not just on the next filter-change event
- **A real bug was found and fixed during browser verification, not caught by any automated test**: `.row { display: flex }` has the same CSS specificity as the browser's default `[hidden] { display: none }`, and (being an author-stylesheet rule) won the cascade — so `row.hidden = true` was correctly set in the DOM/JS sense but the row stayed visibly rendered anyway. Fixed with an explicit `.row[hidden], .detail[hidden] { display: none }` override. This is exactly the kind of thing that looks correct by reading the JS logic alone; only an actual rendered-pixel check caught it
- **Pause/Resume**: while paused, incoming records (live SSE *and* backlog catch-up on reconnect, both routed through one `ingest()` entry point) are buffered instead of dropped, with the button itself showing the live pending count ("Resume (12)"). Resume flushes them in order through the same filter/visibility logic as any other new row. Verified in a real browser: paused, watched the count climb, resumed, confirmed the very last buffered tick rendered
- **Click-to-expand detail panels**: each row toggles its own panel independently (not an accordion — multiple rows can stay expanded at once), showing `file:line`, `logger`, and pretty-printed JSON `data`. The panel's left border is colored to match its row's level — a structural device that encodes which row it belongs to, not decoration
- **`POST /api/clear`**: new endpoint, calls `LogBuffer.clear()`. The Clear button does NOT rely on the existing backlog-diff/poll logic to notice the buffer emptied (that logic has an early-return on an empty backlog that would never clear stale rendered rows) — it directly wipes the DOM and resets all client-side tracking state itself. Verified in a real browser: cleared a page full of rows, watched it go empty, watched new live logs resume normally right after with the counter correctly reset
- **Download button**: fetches a fresh `/api/logs` snapshot (not whatever's currently rendered, which could be stale under a filter or while paused) and triggers a real browser download via a `Blob` + temporary `<a download>`. Verified: a real file was downloaded and its contents are valid, correctly-formatted JSON
- **Tiny inline SVG favicon** — kills the `/favicon.ico` 404 noted back in Phase 3's review. Confirmed zero console errors on a fresh page load
- **`open_browser=True`** now calls `webbrowser.open()` right after the server binds; verified both that it's NOT called by default and that it IS called with the exact bound URL when enabled (mocked in tests, and confirmed the default-off case doesn't regress any existing test)
- New violet accent (`#9d8cff`) added for interactive/active states only (focus rings, the Pause button's active state) — deliberately distinct from all four level colors and from the connection dot's green/red, so "this control is active" never reads as "this is a log severity." One deliberate motion moment for the whole phase: a subtle pulse on the connection dot while reconnecting, disabled under `prefers-reduced-motion`
- 38 tests passing (was 34), `ruff check`, `ruff format --check`, and `mypy --strict` all clean. Every feature above was exercised in a real rendered browser (Playwright, per the owner's established practice for UI review) after the code review — not just assumed from reading the JS

## What's deliberately not wired up yet

- `stop()` doesn't proactively close in-flight SSE connections — unchanged since Phase 4, not a correctness issue
- No dedicated visual QA pass beyond this review (e.g. narrow-window/mobile layout wasn't stress-tested beyond confirming `flex-wrap` doesn't break outright)

## What's set up around the code

- **Layout:** `src/lightlogger/` (src-layout, Hatchling build backend) — every module has real logic now: `buffer.py`, `server.py`, `sse.py`, `handler.py`, `static/index.html`
- **CI** (`.github/workflows/ci.yml`): runs the same lint/type/test gate on Python 3.9–3.13 on every push/PR
- **Publish** (`.github/workflows/publish.yml`): builds + publishes to PyPI via Trusted Publishing (OIDC) when a GitHub Release is cut — no API token stored anywhere
- **Docs:** MIT LICENSE, CHANGELOG (Keep a Changelog format), CONTRIBUTING.md, a placeholder README (real one written at Phase 7 with the demo GIF)
- **Repo:** pushed to `https://github.com/Rahuwale123/lightlogger` (private)

## Naming note

Original name `lightlog` was already taken on PyPI (an unrelated C++-backed logging lib), so the project is branded `lightlogger` everywhere — import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, but that's just the workspace name and doesn't affect the package.

## Not built yet

The real test-coverage target, README (with the demo GIF this UI is meant to star in), CHANGELOG finalization, and the PyPI publish itself — all Phase 7.

_Update this file at the end of each phase._
