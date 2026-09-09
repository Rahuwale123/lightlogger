# Contributing to lightlogger

Thanks for considering a contribution! This project intentionally stays small and dependency-free — please read the ground rules before opening a PR.

## Ground rules

- **Zero third-party runtime dependencies.** Standard library only. Dev-only tools (`pytest`, `ruff`, `mypy`) are the sole exception.
- **Binds to `127.0.0.1` by default.** Any change touching networking must preserve this.
- **No `inspect.stack()`** in the logging hot path — use `sys._getframe()`.
- **Vanilla HTML/CSS/JS** for the dashboard UI — no frameworks, no build step, no CDN links.

## Setup

```bash
git clone https://github.com/Rahuwale123/lightlogger.git
cd lightlogger
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before opening a PR

```bash
ruff check .
ruff format --check .
mypy src/lightlogger
pytest
```

## Commit style

This repo uses [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, ...).
