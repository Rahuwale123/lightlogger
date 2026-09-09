"""lightlogger.help() -- built-in cheatsheet (Phase 7.5, Part A)."""

from __future__ import annotations

import pytest

import lightlogger

_PUBLIC_FUNCTION_NAMES = [
    "start",
    "stop",
    "debug",
    "info",
    "warn",
    "error",
    "var",
    "request",
    "group",
]


def test_help_runs_without_raising() -> None:
    lightlogger.help()


def test_help_mentions_every_public_function(capsys: pytest.CaptureFixture[str]) -> None:
    lightlogger.help()
    out = capsys.readouterr().out
    for name in _PUBLIC_FUNCTION_NAMES:
        assert name in out, f"help() output is missing the function name {name!r}"


def test_help_mentions_install_and_quickstart_and_repo_link(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lightlogger.help()
    out = capsys.readouterr().out
    assert "pip install lightlogger" in out
    assert "lightlogger.start()" in out
    assert "https://github.com/Rahuwale123/lightlogger" in out


def test_help_documents_the_root_logger_warning_gotcha(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lightlogger.help()
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "basicConfig" in out
