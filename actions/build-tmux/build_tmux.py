"""Build, validate and cache a private tmux installation for GitHub Actions.

The action runs this helper in two phases around its cache steps:

- `plan` names the source and the build environment, and prints the cache key.
- `prepare` validates the restored installation, or rebuilds it when it is
  missing or rejected, and records what it built.

A release in `tmux-releases.json` builds from its pinned archive. Any other tag,
branch or full commit builds from the commit it names, resolved once in `plan`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

REPOSITORY = "https://github.com/tmux/tmux.git"
RELEASES: dict[str, str] = json.loads(
    (pathlib.Path(__file__).parent / "tmux-releases.json").read_text()
)

BUILD_DEPENDENCIES = (
    "autoconf",
    "automake",
    "bison",
    "build-essential",
    "libevent-dev",
    "libncurses-dev",
    "libutempter-dev",
    "pkg-config",
)
"""The packages a tmux build needs; a restored build also links their libraries."""

KEYED_PACKAGES = (
    "gcc",
    "libc6",
    "libevent-dev",
    "libncurses-dev",
    "libutempter-dev",
    "bison",
    "autoconf",
    "automake",
    "pkg-config",
)
"""The installed packages whose versions name a build in its cache key."""

BUILD_ENV = {
    "CC": "cc",
    "CFLAGS": "-O2",
    "CPPFLAGS": "",
    "LDFLAGS": "",
    "MAKEFLAGS": "",
}
PROBE_TIMEOUT = 5
CACHE_VERSION = "v3"

_REF = re.compile(r"[A-Za-z0-9._/-]{1,64}")
_RELEASE = re.compile(r"\d+\.\d+[a-z]?")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_IMAGE_PART = re.compile(r"[A-Za-z0-9_.-]+")

Identity = dict[str, str]


class CleanupError(RuntimeError):
    """The private smoke-test daemon could not be cleaned up."""


def sha256(path: pathlib.Path) -> str:
    """Return the SHA256 of a file's content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output(args: Sequence[str]) -> str:
    """Run a command and return its standard output."""
    return subprocess.run(
        args, check=True, capture_output=True, text=True
    ).stdout.strip()


def check_ref(ref: str) -> str:
    """Return a tmux ref that is safe in a path, a cache key and a command.

    >>> check_ref("3.8")
    '3.8'
    >>> check_ref("feature/x")
    'feature/x'
    >>> check_ref("--upload-pack=x")
    Traceback (most recent call last):
    ...
    ValueError: Not a tmux ref: '--upload-pack=x'
    >>> check_ref("")
    Traceback (most recent call last):
    ...
    ValueError: Not a tmux ref: ''
    """
    if not _REF.fullmatch(ref) or ref.startswith("-"):
        message = f"Not a tmux ref: {ref!r}"
        raise ValueError(message)
    return ref


def slug(ref: str) -> str:
    """Return the ref as one path segment and one cache key part.

    >>> slug("feature/x")
    'feature_x'
    """
    return ref.replace("/", "_")


def directory_name(ref: str) -> str:
    """Name the directory of a release, tag, branch or commit.

    A release keeps its plain name. Another ref gets a digest of its exact
    spelling, so `a/b` and `a_b` cannot share a directory.

    >>> directory_name("3.8")
    'tmux-3.8'
    >>> directory_name("a/b")
    'tmux-a_b-c14cddc0'
    >>> directory_name("a_b") != directory_name("a/b")
    True
    """
    if ref in RELEASES:
        return f"tmux-{ref}"
    digest = hashlib.sha256(ref.encode()).hexdigest()[:8]
    return f"tmux-{re.sub(r'[^A-Za-z0-9.-]', '_', ref)}-{digest}"


def resolve(ref: str) -> str:
    """Resolve a tag, branch or full commit to the commit it names."""
    check_ref(ref)
    if _COMMIT.fullmatch(ref):
        return ref
    names = (f"refs/tags/{ref}^{{}}", f"refs/tags/{ref}", f"refs/heads/{ref}")
    listing = output(["git", "ls-remote", "--", REPOSITORY, *names])
    found: dict[str, str] = {}
    for line in listing.splitlines():
        commit, _, name = line.partition("\t")
        found[name] = commit
    for name in names:
        if _COMMIT.fullmatch(found.get(name, "")):
            return found[name]
    message = f"{REPOSITORY} has no tag or branch named {ref!r}"
    raise ValueError(message)


def source_of(ref: str) -> str:
    """Name the exact source: a release's pinned checksum or a commit.

    A ref shaped like a release but missing from the table is refused, not
    built from a tag without a checksum.
    """
    if ref in RELEASES:
        return RELEASES[ref]
    if _RELEASE.fullmatch(ref):
        message = (
            f"tmux {ref} has no checksum in tmux-releases.json; "
            "add the SHA256 of its release archive"
        )
        raise ValueError(message)
    return resolve(ref)


def runner_image() -> str:
    """Return the runner image and its version, as the runner reports them."""
    parts = [os.environ.get(name, "") for name in ("ImageOS", "ImageVersion")]
    if not all(_IMAGE_PART.fullmatch(part) for part in parts):
        message = "Missing or invalid runner image identity"
        raise ValueError(message)
    return "-".join(parts)


def identity(ref: str, configure: Sequence[str] = ()) -> Identity:
    """Name everything a build depends on; any change must change the cache key."""
    image = runner_image()
    return {
        "version": check_ref(ref),
        "source": source_of(ref),
        "image": image,
        "arch": platform.machine(),
        "recipe": sha256(pathlib.Path(__file__)),
        "compiler": output(["cc", "--version"]),
        "packages": output(
            ["dpkg-query", "-W", "-f=${Package}=${Version}\n", *KEYED_PACKAGES]
        ),
        "configure": shlex.join(configure),
    }


def cache_key(ident: Identity) -> str:
    """Return the cache key of an identity.

    >>> cache_key({"version": "feature/x"}).startswith("tmux-v3-feature_x-")
    True
    >>> cache_key({"version": "3.8"}) != cache_key({"version": "3.8", "arch": "arm"})
    True
    """
    digest = hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()
    return f"tmux-{CACHE_VERSION}-{slug(ident['version'])}-{digest}"


def reported_version(binary: pathlib.Path) -> str:
    """Return the version `tmux -V` reports, without the `tmux ` prefix."""
    reported = subprocess.run(
        [str(binary), "-V"],
        check=True,
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT,
    ).stdout.strip()
    if not reported.startswith("tmux "):
        message = f"Not a tmux executable: {reported!r}"
        raise ValueError(message)
    return reported.removeprefix("tmux ")


def probe(binary: pathlib.Path, version: str) -> None:
    """Start a private daemon of the binary and check it reports its version."""
    reported = reported_version(binary)
    if version in RELEASES and reported != version:
        message = f"Expected tmux {version}, got {reported!r}"
        raise ValueError(message)
    env = {k: v for k, v in os.environ.items() if k not in {"TMUX", "TMUX_PANE"}}
    env.update({"SHELL": "/bin/sh", "TERM": "xterm-256color", "LC_ALL": "C.UTF-8"})
    with tempfile.TemporaryDirectory(prefix="lt-ci-") as temporary:
        socket = pathlib.Path(temporary) / "socket"
        command = [str(binary), "-f", "/dev/null", "-S", str(socket)]
        try:
            subprocess.run(
                [*command, "new-session", "-d", "-s", "probe", "exec cat"],
                check=True,
                capture_output=True,
                env=env,
                timeout=PROBE_TIMEOUT,
            )
            connected = subprocess.run(
                [*command, "display-message", "-p", "#{version}"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=PROBE_TIMEOUT,
            ).stdout.strip()
            if reported != connected:
                message = f"Connected daemon version differs: {connected!r}"
                raise ValueError(message)
        finally:
            if socket.exists():
                try:
                    subprocess.run(
                        [*command, "kill-server"],
                        check=True,
                        capture_output=True,
                        env=env,
                        timeout=PROBE_TIMEOUT,
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    message = "Failed to clean up the private tmux smoke test"
                    raise CleanupError(message) from error


def valid(prefix: pathlib.Path, ident: Identity) -> bool:
    """Say whether an installed prefix is the build the identity describes."""
    binary = prefix / "bin" / "tmux"
    try:
        if prefix.is_symlink() or binary.parent.is_symlink() or binary.is_symlink():
            return False
        record = json.loads((prefix / "build.json").read_text())
        if record != {"identity": ident, "sha256": sha256(binary)}:
            return False
        probe(binary, ident["version"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"tmux cache rejected: {error}", flush=True)
        return False
    return True


def _fetch_commit(work: pathlib.Path, commit: str, env: dict[str, str]) -> pathlib.Path:
    source = work / "tmux"
    subprocess.run(["git", "init", "--quiet", str(source)], check=True)
    subprocess.run(
        ["git", "-C", str(source), "fetch", "--quiet", "--depth=1", REPOSITORY, commit],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(source), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
        check=True,
    )
    if output(["git", "-C", str(source), "rev-parse", "HEAD"]) != commit:
        message = "Fetched tmux commit differs from the cache identity"
        raise ValueError(message)
    subprocess.run(["sh", "autogen.sh"], check=True, cwd=source, env=env)
    return source


def _fetch_release(work: pathlib.Path, version: str, checksum: str) -> pathlib.Path:
    archive = work / "tmux.tar.gz"
    url = f"https://github.com/tmux/tmux/releases/download/{version}/tmux-{version}.tar.gz"
    subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--retry",
            "2",
            "--output",
            str(archive),
            url,
        ],
        check=True,
    )
    if sha256(archive) != checksum:
        message = "Downloaded tmux archive does not match its pinned SHA256"
        raise ValueError(message)
    subprocess.run(
        [
            "tar",
            "--extract",
            "--gzip",
            "--file",
            str(archive),
            "--directory",
            str(work),
            "--no-same-owner",
            "--no-same-permissions",
        ],
        check=True,
    )
    return work / f"tmux-{version}"


def build(prefix: pathlib.Path, ident: Identity) -> None:
    """Build the identity's source and install it under the prefix."""
    env = dict(os.environ, **BUILD_ENV)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="tmux-source-", dir=prefix.parent
    ) as temporary:
        work = pathlib.Path(temporary)
        version = ident["version"]
        if version in RELEASES:
            source = _fetch_release(work, version, ident["source"])
        else:
            source = _fetch_commit(work, ident["source"], env)
        configure = [
            "./configure",
            f"--prefix={prefix}",
            *shlex.split(ident["configure"]),
        ]
        subprocess.run(configure, check=True, cwd=source, env=env)
        jobs = min(4, len(os.sched_getaffinity(0)))
        subprocess.run(["make", f"-j{jobs}"], check=True, cwd=source, env=env)
        subprocess.run(["make", "install"], check=True, cwd=source, env=env)


def prepare(prefix: pathlib.Path, ident: Identity) -> bool:
    """Keep a valid installation; otherwise replace it. Return whether it built."""
    if valid(prefix, ident):
        print(f"Validated cached tmux {ident['version']}", flush=True)
        return False
    if prefix.is_symlink():
        prefix.unlink()
    elif prefix.exists():
        shutil.rmtree(prefix)
    build(prefix, ident)
    binary = prefix / "bin" / "tmux"
    probe(binary, ident["version"])
    record = {"identity": ident, "sha256": sha256(binary)}
    (prefix / "build.json").write_text(json.dumps(record, sort_keys=True) + "\n")
    return True


def prefix_for(ref: str, requested: str | None) -> pathlib.Path:
    """Return the install prefix: the requested one, or a directory in RUNNER_TEMP."""
    if requested:
        return pathlib.Path(requested).expanduser().absolute()
    root = pathlib.Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    return root / directory_name(ref)


def plan_path(prefix: pathlib.Path) -> pathlib.Path:
    """Return where `plan` leaves the identity for `prepare`; one file per prefix."""
    root = pathlib.Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    digest = hashlib.sha256(str(prefix).encode()).hexdigest()[:8]
    return root / f"tmux-plan-{digest}.json"


def _append(variable: str, text: str) -> None:
    with pathlib.Path(os.environ[variable]).open("a") as handle:
        handle.write(text)


def run_plan(ref: str, requested: str | None, configure_args: str) -> None:
    """Identify the build, and publish its prefix, binary, source and cache key."""
    configure = shlex.split(configure_args)
    if any(arg.startswith("--prefix") for arg in configure):
        message = "configure-args cannot set --prefix; use the prefix input"
        raise ValueError(message)
    prefix = prefix_for(check_ref(ref), requested)
    ident = identity(ref, configure)
    plan_path(prefix).write_text(json.dumps(ident, sort_keys=True) + "\n")
    print(json.dumps(ident, indent=2), flush=True)
    _append(
        "GITHUB_OUTPUT",
        f"prefix={prefix}\nbinary={prefix / 'bin' / 'tmux'}\n"
        f"source={ident['source']}\nkey={cache_key(ident)}\n",
    )


def run_prepare(ref: str, requested: str | None, *, add_to_path: bool) -> None:
    """Validate or rebuild the planned build, and publish the version it reports."""
    prefix = prefix_for(check_ref(ref), requested)
    ident: Identity = json.loads(plan_path(prefix).read_text())
    if ident["version"] != ref:
        message = "Build plan version does not match the requested tmux"
        raise ValueError(message)
    rebuilt = prepare(prefix, ident)
    if rebuilt and os.environ.get("CACHE_HIT") == "true":
        print(
            "::warning::Invalid exact cache rebuilt locally. Change the build "
            "recipe to invalidate the immutable cache entry on subsequent runs."
        )
    if add_to_path:
        _append("GITHUB_PATH", f"{prefix / 'bin'}\n")
    version = reported_version(prefix / "bin" / "tmux")
    _append("GITHUB_OUTPUT", f"version={version}\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one phase of the build."""
    parser = argparse.ArgumentParser(description=__doc__)
    phases = parser.add_subparsers(dest="phase", required=True)
    plan = phases.add_parser("plan", help="identify the source and the environment")
    prep = phases.add_parser("prepare", help="validate a restored build or build")
    for phase in (plan, prep):
        phase.add_argument("ref", help="a release, tag, branch or 40-hex commit")
        phase.add_argument("--prefix", help="install here; default a RUNNER_TEMP dir")
    plan.add_argument("--configure-args", default="", help="extra ./configure args")
    prep.add_argument("--add-to-path", action="store_true", help="export bin/ to PATH")
    phases.add_parser("dependencies", help="print the apt packages a build needs")
    options = parser.parse_args(argv)
    if options.phase == "dependencies":
        print(" ".join(BUILD_DEPENDENCIES))
    elif options.phase == "plan":
        run_plan(options.ref, options.prefix, options.configure_args)
    else:
        run_prepare(options.ref, options.prefix, add_to_path=options.add_to_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
