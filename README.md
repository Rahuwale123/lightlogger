# lightlogger

Live web dashboard for your Python logs — pip install, add one line, open localhost:4356. Zero dependencies.

A live log viewer web UI you run from inside your own process: no separate server to install, no account, no config file — just a browser tab that tails your logs as they happen.

[![PyPI](https://img.shields.io/pypi/v/lightlogger.svg)](https://pypi.org/project/lightlogger/)
[![CI](https://github.com/Rahuwale123/lightlogger/actions/workflows/ci.yml/badge.svg)](https://github.com/Rahuwale123/lightlogger/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

📖 [Documentation](https://rahuwale123.github.io/lightlogger/)

![lightlogger dashboard: a nested process_order group with a warning badge, a live error, and streaming request logs](https://raw.githubusercontent.com/Rahuwale123/lightlogger/main/assets/demo.gif)

## Install

```bash
pip install lightlogger
```

```python
import lightlogger
lightlogger.start()
lightlogger.info("user logged in")
```

That's it — open `http://127.0.0.1:4356` and watch it stream in live, in a dark, searchable dashboard. No config file, no separate server process to run, no npm install.

Your existing `logging` calls show up too, with zero code changes:

```python
lightlogger.start(capture_logging=True)  # the default
import logging
logging.getLogger("some.third.party.lib").warning("disk almost full")  # appears in the UI automatically
```

And when one log message is really four related operations, group them:

```python
with lightlogger.group("process_order #4821"):
    lightlogger.info("validating cart")
    lightlogger.info("charging payment", data={"amount": 49.99})
    with lightlogger.group("send_notifications"):
        lightlogger.info("email sent")
        lightlogger.info("sms sent")
```

They render as a collapsible tree — click to expand, nested groups indent, a red badge appears if anything inside failed.

## Features

| | |
|---|---|
| **Live streaming** | Server-Sent Events, not polling — logs appear the instant they're written |
| **Zero-code `logging` capture** | Attaches to the root logger; your own and third-party libraries' logs show up automatically |
| **Nested log grouping** | `with lightlogger.group(name):` — collapsible, nested, thread- and async-safe |
| **Search & level filter** | Client-side, instant, works across grouped and ungrouped logs alike |
| **Pause / Resume** | Freeze the view to read something — nothing is dropped, a counter shows what's waiting |
| **Click to expand** | File, line, logger name, and pretty-printed JSON data for any entry |
| **Download as JSON** | One click, the full current backlog |
| **Bounded memory** | A fixed-size ring buffer — lightlogger can never be the reason your app runs out of RAM |
| **Zero dependencies** | Python standard library only, from the HTTP server to the JSON encoding |

## Works with

lightlogger doesn't care what's generating your logs — it mirrors whatever reaches Python's root logger, so there's no framework-specific integration to write. It works equally well as a log dashboard for Flask, FastAPI, and Django apps as it does for a one-off script:

| | How |
|---|---|
| **Plain scripts** | `lightlogger.start()` anywhere near the top — every `debug`/`info`/`warn`/`error` call and any existing `logging` call shows up |
| **Flask** | Call `lightlogger.start()` once, e.g. in your app factory — Flask's own `app.logger` propagates to the root logger by default, so it appears with zero extra wiring |
| **FastAPI** | Same idea in a startup event; pair it with `lightlogger.request(method, url, status_code, duration_ms)` in a middleware for color-coded, status-aware request logging |
| **Django** | Call it from `settings.py` or an `AppConfig.ready()` — Django's own `LOGGING` config still applies, lightlogger just watches what comes out of it |
| **Jupyter notebooks** | `lightlogger.start()` in a cell keeps the dashboard running on a background thread for the rest of the session; call `lightlogger.stop()` before restarting the kernel for a clean slate |

## API reference

| Function | Description | Example |
|---|---|---|
| `start(...)` | Starts the dashboard on a background thread. See parameters below. Calling it again while already running is a no-op. | `lightlogger.start(port=8080, open_browser=True)` |
| `stop()` | Stops the server and detaches the logging handler. Mostly for tests/notebooks. | `lightlogger.stop()` |
| `debug(msg, data=None)` | Logs a debug-level message (grey). | `lightlogger.debug("cache miss", data={"key": "user:42"})` |
| `info(msg, data=None)` | Logs an info-level message (blue). | `lightlogger.info("user logged in")` |
| `warn(msg, data=None)` | Logs a warn-level message (yellow). | `lightlogger.warn("retrying after timeout")` |
| `error(msg, data=None)` | Logs an error-level message (red). | `lightlogger.error("payment failed", data={"order_id": 123})` |
| `var(name, value)` | Logs any variable as an expandable JSON blob. | `lightlogger.var("cart", cart_dict)` |
| `request(method, url, status, duration_ms)` | Logs one HTTP request/response. Level follows the status code: `< 400` → info, `4xx` → warn, `5xx` → error. | `lightlogger.request("GET", "/api/users", 500, 812.0)` → logs as **error** |
| `group(name)` | Context manager for nested, collapsible log groups. Thread- and async-safe. | `` with lightlogger.group("checkout"): ... `` |
| `help()` | Prints this reference to your terminal. | `lightlogger.help()` |

`start()` parameters:

| Parameter | Default | Meaning |
|---|---|---|
| `port` | `4356` | Preferred port; auto-increments to the next free one if taken |
| `host` | `"127.0.0.1"` | Bind address — `"0.0.0.0"` is an explicit, loudly-warned opt-in for LAN exposure |
| `max_logs` | `5000` | Ring buffer size — the most recent N records are kept, oldest dropped first |
| `capture_logging` | `True` | Attach a handler to the root logger so existing `logging` calls appear automatically |
| `open_browser` | `False` | Open the dashboard in your default browser as soon as it's live |

## Built-in help

Forgot the API? It's in the package, not just this README:

```python
>>> import lightlogger
>>> lightlogger.help()
```

Prints a full cheatsheet to your terminal — every function, one-line descriptions, tiny examples, the `capture_logging` gotcha, no need to leave your shell. And once the dashboard is running, open `http://127.0.0.1:4356/help` for the same reference as a page, with copyable code blocks.

## Why lightlogger

Debugging a running Python process usually means one of three things: `print()` statements you'll forget to remove, a terminal window full of scrolling text you can't search, or reaching for a heavyweight observability platform to answer a question that takes ten seconds to answer once you can actually *see* your logs. lightlogger is the alternative to print debugging that doesn't cost you anything to try: two lines, and you can view your Python logs in the browser instead of squinting at a terminal.

We looked at what else exists. [Logdy](https://logdy.dev/) is a Go binary you install separately from your app. [Chronologer](https://github.com/nkconnor/chronologer) needs its own server process. [cutelog](https://github.com/busimus/cutelog) needs PyQt. Logfire is closed-source and cloud-hosted. `lnav` and `klp` are terminal-only. Django and Flask debug toolbars only work inside those specific frameworks, in that specific request/response cycle.

None of them do the one thing that actually matches how a Python developer debugs: `import`, call one function, and get a live web page — from *inside* the process you're already running, with no extra install, no extra service, no dependencies to audit. That's the gap lightlogger fills. And once your logs have a real UI instead of a scrolling terminal, grouping related operations into a collapsible tree stops being a nice-to-have — it's the difference between reading a wall of text and reading a story.

## Security

lightlogger binds to `127.0.0.1` only, by default — nothing is reachable outside your machine unless you explicitly pass `host="0.0.0.0"` (which prints a loud warning when you do). It's a local development tool, not a production observability system: don't run it against a public-facing process, and don't leave it running longer than your debugging session needs.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the ground rules (short version: zero dependencies, stay on stdlib, keep it simple). Bug reports and PRs both go through [GitHub Issues](https://github.com/Rahuwale123/lightlogger/issues).

## License

MIT — see [LICENSE](LICENSE).
