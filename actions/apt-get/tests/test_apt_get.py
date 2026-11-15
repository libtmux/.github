"""Tests for the bounded apt-get wrapper."""

from __future__ import annotations

import pathlib
import sys
from typing import TYPE_CHECKING

import apt_get
import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence


class Recorder:
    """Stand in for the process runner: log each command, answer from a script."""

    def __init__(self, statuses: Sequence[int]) -> None:
        self.statuses = iter(statuses)
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(self, command: Sequence[str], *, stdin: str | None = None) -> int:
        self.calls.append((list(command), stdin))
        return next(self.statuses, 0)

    @property
    def apt_calls(self) -> list[list[str]]:
        return [command for command, _ in self.calls if "apt-get" in command]


@pytest.fixture
def mirrors(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "apt-mirrors.txt"
    path.write_text("http://one/\nhttp://two/\nhttp://three/\n")
    return path


def test_success_runs_once_without_touching_the_mirrors(
    mirrors: pathlib.Path,
) -> None:
    recorder = Recorder([0])
    status = apt_get.run(
        ["install", "--yes", "tmux"],
        timeout=60,
        mirrors=mirrors,
        root=False,
        execute=recorder,
    )
    assert status == 0
    assert recorder.calls == [
        (
            [
                "sudo",
                "timeout",
                "--kill-after=10",
                "60",
                "apt-get",
                "-o",
                "Acquire::Retries=3",
                "install",
                "--yes",
                "tmux",
            ],
            None,
        )
    ]
    assert mirrors.read_text().startswith("http://one/")


def test_failure_rotates_the_mirror_and_retries(
    mirrors: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recorder = Recorder([124, 0, 0])
    status = apt_get.run(
        ["update"], timeout=5, mirrors=mirrors, root=True, execute=recorder
    )
    assert status == 0
    assert len(recorder.apt_calls) == 2
    assert recorder.calls[1] == (
        ["tee", str(mirrors)],
        "http://two/\nhttp://three/\nhttp://one/\n",
    )
    assert "apt-get: attempt 1 of 3 failed" in capsys.readouterr().err


def test_every_attempt_failing_exits_1_and_rotates_between_attempts_only(
    mirrors: pathlib.Path,
) -> None:
    recorder = Recorder([100] * 6)
    status = apt_get.run(
        ["update"], timeout=5, mirrors=mirrors, root=True, execute=recorder
    )
    assert status == 1
    assert len(recorder.apt_calls) == 3
    assert len([c for c in recorder.calls if c[0][0] == "tee"]) == 2


def test_missing_or_empty_mirror_list_is_not_rotated(tmp_path: pathlib.Path) -> None:
    empty = tmp_path / "empty"
    empty.write_text("")
    for mirrors in (tmp_path / "absent", empty):
        recorder = Recorder([100] * 3)
        status = apt_get.run(
            ["update"], timeout=5, mirrors=mirrors, root=True, execute=recorder
        )
        assert status == 1
        assert recorder.calls == [(c, None) for c in recorder.apt_calls]


def test_update_runs_first_and_a_failed_update_stops_the_install(
    monkeypatch: pytest.MonkeyPatch, mirrors: pathlib.Path
) -> None:
    seen: list[list[str]] = []

    def fake_run(args: Sequence[str], **_: object) -> int:
        seen.append(list(args))
        return 1 if args[0] == "update" else 0

    monkeypatch.setattr(apt_get, "run", fake_run)
    assert apt_get.main(["--update", "--args", "install --yes tmux"]) == 1
    assert seen == [["update"]]
    seen.clear()
    monkeypatch.setattr(apt_get, "run", lambda args, **_: seen.append(list(args)) or 0)
    assert apt_get.main(["--update", "--args", "install --yes 'a b'"]) == 0
    assert seen == [["update"], ["install", "--yes", "a b"]]


@pytest.mark.parametrize(
    "argv", [[], ["--args", "  "], ["--args", "x", "--timeout", "0"]]
)
def test_bad_command_line_is_a_usage_error(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        apt_get.main(argv)
    assert raised.value.code == 2


def test_the_module_runs_as_a_script_and_reports_its_exit_status(
    tmp_path: pathlib.Path,
) -> None:
    """Prove the entry point end to end against a fake `apt-get` on PATH."""
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in {
        "sudo": 'exec "$@"',
        "timeout": 'shift 2; exec "$@"',
        "apt-get": 'echo "apt-get $*" >> "$LOG"; exit "${FAKE_STATUS:-0}"',
    }.items():
        script = bin_dir / name
        script.write_text(f"#!/bin/sh\n{body}\n")
        script.chmod(0o755)
    log = tmp_path / "log"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "LOG": str(log)}
    script_path = pathlib.Path(apt_get.__file__)
    ok = subprocess.run(
        [sys.executable, str(script_path), "--args", "install --yes tmux"],
        env=env,
        check=False,
    )
    assert ok.returncode == 0
    assert log.read_text() == "apt-get -o Acquire::Retries=3 install --yes tmux\n"
    failing = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--args",
            "update",
            "--mirrors",
            str(tmp_path / "absent"),
        ],
        env={**env, "FAKE_STATUS": "100"},
        check=False,
        capture_output=True,
    )
    assert failing.returncode == 1
