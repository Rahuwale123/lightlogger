# lightlogger — status (Phase 6.5 of 7 — log grouping, a scope amendment)

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

## Phase 6.5 — log grouping (scope amendment, done after Phase 6)

Added `lightlogger.group(name)`, a nested-log-grouping context manager, and a full collapsible-tree UI to render it. This was a deliberate, documented exception to the frozen v1 API (see the amendment note at the top of CLAUDE.md) — evaluated as a genuine differentiator (no competing zero-dep local dashboard has this) rather than scope creep.

- **Backend**: `LogRecord` now always carries `group_id`/`parent_group_id` (`str | None`, never omitted — no `typing.NotRequired`, which doesn't exist in stdlib `typing` before Python 3.11 and this project supports 3.9+ with zero dependencies). A group marker sets its own `group_id`; every record sets `parent_group_id` to whatever group directly contains it. Thread/async safety comes from a `contextvars.ContextVar`, not a module global — verified with two real threads forced to interleave via `threading.Barrier`, confirming zero cross-contamination. A plain `logging.info()` call made inside a `group()` block nests correctly too, since `handler.py` reads the same ContextVar.
- **UI**: genuine nested DOM (a group is a header + a children container, not flat rows with computed indentation), so collapsing is just hiding one container and indentation compounds on its own via nested CSS padding. Child count is the recursive count of actual log entries (excluding nested group markers themselves) — verified against the exact worked example from the spec: `process_order #123` correctly shows "(4 logs)". A worst-level badge (red if any descendant anywhere is error-level, else yellow for warn) updates live and monotonically as new children stream in.
- **Search/filter is tree-aware**: a group is visible if its own name matches or any descendant does; a matching descendant force-expands its full ancestor chain. Manual expand/collapse and search-driven auto-expand are two genuinely separate concerns (a tri-state `manualState`: never-touched / explicitly-expanded / explicitly-collapsed) — **a real bug was found and fixed during browser verification**: the first implementation used a plain boolean ORed with the search condition, which meant a group auto-expanded by a search match could never be manually collapsed by clicking it (the click flipped a flag that the OR then ignored). Fixed so a manual click always wins over search-driven expansion, matching how real search-UIs (VS Code, GitHub code search) behave — verified: click collapses it even mid-search, and the manual choice correctly survives clearing the search afterward.
- **Everything from Phase 6 re-verified working unchanged**: plain-row click-to-expand, Clear (now also resets the group registry, confirmed zero stale group headers survive a Clear), Download (unchanged — still the flat `/api/logs` JSON, which already includes the new fields), pause/resume (buffered records reconstruct the tree correctly on flush, since a group's marker always precedes its children in arrival order), connection dot, favicon. A known, accepted quirk from the literal spec: with only a level filter active (no search text) a group header always renders even with zero matching-level descendants, since level filtering doesn't apply to a group's own row — this is documented behavior, not a bug.
- New teal/cyan accent (`#2dd4bf`) for group chrome only (chevron, group name, header tint) — kept distinct from the four level colors, the violet interactive accent, and the badge, which deliberately reuses the real warn/error colors since it's an aggregated severity signal, not a new meaning.
- 43 tests passing (was 38), `ruff check`, `ruff format --check`, and `mypy --strict` all clean.

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
