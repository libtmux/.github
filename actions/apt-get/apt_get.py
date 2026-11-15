"""Run apt-get on a GitHub-hosted runner without letting one hung mirror stall a job.

Why: actions/runner-images#15040. On ubuntu-24.04 images 20260927, 20261004 and
20261012, `apt-get update` sometimes ignores the Azure mirror and falls back to
https://archive.ubuntu.com/ubuntu, then hangs until the job timeout. The image's
15 s Acquire timeout does not apply after the failover.

What: run `apt-get -o Acquire::Retries=3 ARGS` as root under `timeout`. When an
attempt fails or times out, move the first line of /etc/apt/apt-mirrors.txt to
the end so the next attempt starts on another mirror, and try again, up to three
attempts in all.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence

MIRRORS = pathlib.Path("/etc/apt/apt-mirrors.txt")
ATTEMPTS = 3
KILL_AFTER = 10

Execute = Callable[..., int]
"""Run a command and return its exit status; `stdin` feeds the command's input."""


def rotate(mirrors: str) -> str:
    r"""Move the first mirror to the end, so the next attempt starts on another.

    >>> rotate("a\nb\nc\n")
    'b\nc\na\n'
    >>> rotate("only\n")
    'only\n'
    >>> rotate("a\nb")
    'b\na\n'
    """
    lines = mirrors.splitlines()
    return "".join(f"{line}\n" for line in [*lines[1:], *lines[:1]])


def privileged(command: Sequence[str], *, root: bool | None = None) -> list[str]:
    """Run a command as root: through sudo, unless the process is root already.

    >>> privileged(["apt-get", "update"], root=False)
    ['sudo', 'apt-get', 'update']
    >>> privileged(["apt-get", "update"], root=True)
    ['apt-get', 'update']
    """
    if root is None:
        root = os.geteuid() == 0
    return [*command] if root else ["sudo", *command]


def apt_command(
    args: Sequence[str], timeout: int, *, root: bool | None = None
) -> list[str]:
    """Build one bounded attempt: apt-get as root under `timeout`.

    >>> " ".join(apt_command(["update"], 180, root=True))
    'timeout --kill-after=10 180 apt-get -o Acquire::Retries=3 update'
    """
    return privileged(
        [
            "timeout",
            f"--kill-after={KILL_AFTER}",
            str(timeout),
            "apt-get",
            "-o",
            "Acquire::Retries=3",
            *args,
        ],
        root=root,
    )


def _execute(command: Sequence[str], *, stdin: str | None = None) -> int:
    return subprocess.run(
        command,
        input=stdin,
        text=True,
        check=False,
        stdout=None if stdin is None else subprocess.DEVNULL,
    ).returncode


def run(  # noqa: PLR0913
    args: Sequence[str],
    *,
    timeout: int,
    attempts: int = ATTEMPTS,
    mirrors: pathlib.Path = MIRRORS,
    root: bool | None = None,
    execute: Execute = _execute,
) -> int:
    """Run apt-get until it succeeds, rotating the mirror after each failure.

    Returns 0 on success and 1 when every attempt failed.

    >>> statuses = iter([100, 0])
    >>> run(["update"], timeout=5, root=True, execute=lambda *_, **__: next(statuses))
    0
    """
    for attempt in range(1, attempts + 1):
        if execute(apt_command(args, timeout, root=root)) == 0:
            return 0
        print(f"apt-get: attempt {attempt} of {attempts} failed", file=sys.stderr)
        if attempt < attempts and mirrors.is_file() and mirrors.stat().st_size > 0:
            rotated = rotate(mirrors.read_text())
            execute(privileged(["tee", str(mirrors)], root=root), stdin=rotated)
    return 1


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        message = f"{value} is not a positive number"
        raise argparse.ArgumentTypeError(message)
    return number


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the command line and run apt-get."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--args",
        required=True,
        help='the apt-get arguments, split like a shell line: "install --yes tmux"',
    )
    parser.add_argument(
        "--timeout",
        type=_positive,
        default=180,
        help="seconds one attempt may take (default 180)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="run `apt-get update` first, under the same bounds",
    )
    parser.add_argument(
        "--mirrors",
        type=pathlib.Path,
        default=MIRRORS,
        help=f"the mirror list to rotate on failure (default {MIRRORS})",
    )
    options = parser.parse_args(argv)
    args = shlex.split(options.args)
    if not args:
        parser.error("--args names no apt-get command")
    if options.update:
        status = run(["update"], timeout=options.timeout, mirrors=options.mirrors)
        if status != 0:
            return status
    return run(args, timeout=options.timeout, mirrors=options.mirrors)


if __name__ == "__main__":
    sys.exit(main())
