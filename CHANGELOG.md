# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Ideas (post-v1, not in scope for now)

- Multiple UI layouts / themes beyond dark mode
- AI-assisted log summarization
- Auth/login for the dashboard
- Flask/Django/FastAPI middleware integrations
- Node.js port

## [0.1.1] - 2026-09-09

### Changed

- `lightlogger.request()` now derives its log level from the HTTP status code instead of always logging at `info`: `< 400` → `info`, `4xx` → `warn`, `5xx` → `error`. A failed request now actually looks like a failure in the dashboard.

### Fixed

- README lacked a complete API reference — added a full table covering every public function (`start`, `stop`, `debug`, `info`, `warn`, `error`, `var`, `request`, `group`, `help`) with one-line descriptions, examples, and `start()`'s parameters (`port`, `host`, `max_logs`, `capture_logging`, `open_browser`).

## [0.1.0] - 2026-09-09

Initial release.

### Added

- `lightlogger.start()` / `stop()` — a `ThreadingHTTPServer` on a daemon thread, binding `127.0.0.1:4356` by default with automatic port fallback on conflict; `host="0.0.0.0"` is an explicit, loudly-warned opt-in.
- `debug()` / `info()` / `warn()` / `error()` / `var()` / `request()` — write into a bounded in-memory ring buffer (`max_logs`, default 5000), with caller file/line captured via `sys._getframe` (never `inspect.stack()`).
- `lightlogger.group(name)` — a context manager for nested log grouping, backed by `contextvars` for thread/async safety.
- Zero-code `logging` capture: `start(capture_logging=True)` (the default) attaches a handler to the root logger, so existing and third-party `logging` calls appear automatically.
- Live dashboard UI (`GET /`, single self-contained HTML file, no CDN): dark theme, level-colored rows, search box, level filter, pause/resume with no dropped records, click-to-expand detail panels, download-as-JSON, a collapsible group tree with per-group counts and a worst-level badge.
- `GET /api/logs` (JSON backlog), `GET /api/stream` (Server-Sent Events, replacing polling), `POST /api/clear`.
- `open_browser=True` opens the dashboard automatically on `start()`.
- `lightlogger.help()` prints a full API cheatsheet to the terminal; `GET /help` serves the same reference as an offline HTML page, linked from the dashboard header.
- 100% test coverage, `mypy --strict` clean, CI across Python 3.9–3.13, PyPI publishing via Trusted Publishing (OIDC) — no long-lived API token ever stored.
