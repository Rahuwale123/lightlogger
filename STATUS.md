# lightlogger — status: PUBLISHED (v0.1.1 live on PyPI)

`pip install lightlogger` works, right now, for real. All 7 phases (plus the 6.5 grouping amendment and the 7.5 help/publish phase) are complete and shipped. v0.1.1 is a same-day patch from dogfooding: `request()` now derives its log level from the HTTP status code (`<400` info, `4xx` warn, `5xx` error — a 500 no longer quietly logs as "info"), and the README gained a complete API reference table.

## Live links

- **PyPI**: https://pypi.org/project/lightlogger/
- **GitHub (public)**: https://github.com/Rahuwale123/lightlogger
- **Release**: https://github.com/Rahuwale123/lightlogger/releases/tag/v0.1.0

## What's actually live

- `lightlogger.start()` / `stop()` — `ThreadingHTTPServer` on a daemon thread, `127.0.0.1:4356` by default with port auto-increment on conflict
- `debug()` / `info()` / `warn()` / `error()` / `var()` / `request()` — bounded ring buffer (`max_logs`, default 5000), caller file/line via `sys._getframe`
- `lightlogger.group(name)` — nested log grouping, `contextvars`-based thread/async safety (the headline differentiator, added as a documented scope amendment — see CLAUDE.md's amendment note)
- Zero-code `logging` capture via a root-logger handler (deliberately never forces the logger's level open — see the Phase 5 design decision)
- `lightlogger.help()` (terminal cheatsheet) and `GET /help` (offline HTML docs page, linked from the dashboard header)
- Full dashboard UI: SSE live streaming, search, level filter, pause/resume, click-to-expand, download-as-JSON, collapsible group tree with per-group counts and worst-level badges, connection status dot
- `GET /api/logs`, `GET /api/stream`, `POST /api/clear`
- `open_browser=True`

## Verified end-to-end from the real published package

Fresh venv → `pip install lightlogger` from real PyPI → confirmed zero runtime dependencies (`Requires:` empty) → quickstart (`start()` + `info()`) → `/api/logs` returns the record → `/help` returns 200 with real content → `lightlogger.help()` prints the full cheatsheet. Not tested against a local build — against the actual thing anyone in the world can now install.

## Quality metrics (at publish time)

- 100% test coverage (252/252 statements), 69 tests
- `ruff check` / `ruff format --check` / `mypy --strict` all clean
- CI green on Python 3.9–3.13
- Published via PyPI Trusted Publishing (OIDC) — no API token ever stored as a GitHub secret
- Zero runtime dependencies, confirmed both via `pyproject.toml` and PyPI's own `requires_dist` metadata

## Naming note

Original name `lightlog` was taken on PyPI (an unrelated C++-backed logging lib) — this project is `lightlogger` everywhere: import name, PyPI name, GitHub repo. The local Desktop folder is still called `lightlog`, which is just the workspace name and doesn't affect the package.

## What's left

Nothing required for v1. Post-v1 ideas (multiple UI themes, AI summarization, auth, framework middleware, a Node.js port) are tracked in `CHANGELOG.md`'s `[Unreleased] > Ideas` section, deliberately not built — see CLAUDE.md section 8.

_This file now tracks ongoing/future work, not a build phase — the build is done._
