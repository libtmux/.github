"""Tests for the tmux build helper.

Tests marked `native` start a real tmux, the one on PATH or the one named by
TMUX_BINARY. The integration job runs them against each tmux the action builds.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import tarfile

import build_tmux
import pytest

NATIVE = pytest.mark.native
Identity = dict[str, str]


@pytest.fixture
def native() -> tuple[pathlib.Path, Identity]:
    """Use a real tmux for validation and for the private daemon checks."""
    found = os.environ.get("TMUX_BINARY") or shutil.which("tmux")
    if found is None:
        pytest.fail("native tests need tmux on PATH or in TMUX_BINARY")
    binary = pathlib.Path(found).resolve()
    version = build_tmux.reported_version(binary)
    return binary, {"version": version if version in build_tmux.RELEASES else "master"}


def _install(prefix: pathlib.Path, installed: pathlib.Path) -> pathlib.Path:
    binary = prefix / "bin" / "tmux"
    binary.parent.mkdir(parents=True)
    shutil.copy2(installed, binary)
    return binary


def _record(prefix: pathlib.Path, ident: Identity) -> None:
    digest = hashlib.sha256((prefix / "bin" / "tmux").read_bytes()).hexdigest()
    (prefix / "build.json").write_text(
        json.dumps({"identity": ident, "sha256": digest})
    )


@NATIVE
@pytest.mark.parametrize("fault", ["loader", "version", "identity", "hash", "metadata"])
def test_broken_cached_executable_is_rebuilt(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    native: tuple[pathlib.Path, Identity],
    fault: str,
) -> None:
    """Replace slow compilation only; run validation against a real executable."""
    installed, ident = native
    prefix = tmp_path / "tmux"
    binary = _install(prefix, installed)
    if fault == "loader":
        binary.write_text("#!/bin/sh\nexit 127\n")
    elif fault == "version":
        binary.write_text("#!/bin/sh\necho 'unrelated executable'\n")
    _record(prefix, ident if fault != "identity" else {"version": "other"})
    if fault == "hash":
        with binary.open("ab") as output:
            output.write(b"changed")
    elif fault == "metadata":
        (prefix / "build.json").write_text("{")
    stale = prefix / "old-object.o"
    stale.touch()
    sibling = tmp_path / "borrowed"
    sibling.write_text("keep")

    def compile_fresh(destination: pathlib.Path, _: Identity) -> None:
        assert not destination.exists()
        _install(destination, installed)

    monkeypatch.setattr(build_tmux, "build", compile_fresh)
    assert build_tmux.prepare(prefix, ident)
    assert not stale.exists()
    assert sibling.read_text() == "keep"
    assert binary.read_bytes() == installed.read_bytes()
    assert build_tmux.valid(prefix, ident)


@NATIVE
def test_valid_cache_skips_build_and_leaves_other_servers_alive(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    native: tuple[pathlib.Path, Identity],
) -> None:
    """Avoid compilation on a valid hit; exercise real startup and cleanup."""
    installed, ident = native
    prefix = tmp_path / "tmux"
    binary = _install(prefix, installed)
    _record(prefix, ident)
    inode = binary.stat().st_ino

    def unexpected_build(_: pathlib.Path, __: Identity) -> None:
        pytest.fail("A validated cache must not rebuild")

    monkeypatch.setattr(build_tmux, "build", unexpected_build)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setenv("SHELL", "/bin/sh")
    monkeypatch.setenv("TERM", "xterm-256color")
    command = [str(installed), "-f", "/dev/null", "-S", str(tmp_path / "other.sock")]
    subprocess.run(
        [*command, "new-session", "-d", "-s", "keep", "exec cat"], check=True
    )
    try:
        assert not build_tmux.prepare(prefix, ident)
        assert binary.stat().st_ino == inode
        subprocess.run([*command, "has-session", "-t", "keep"], check=True)
    finally:
        subprocess.run([*command, "kill-server"], check=True)


@NATIVE
def test_symlink_cache_does_not_delete_its_target(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    native: tuple[pathlib.Path, Identity],
) -> None:
    """Replace compilation only; discard the cache link without following it."""
    installed, ident = native
    borrowed = tmp_path / "borrowed"
    original = _install(borrowed, installed)
    _record(borrowed, ident)
    prefix = tmp_path / "tmux"
    prefix.symlink_to(borrowed, target_is_directory=True)

    def compile_fresh(destination: pathlib.Path, _: Identity) -> None:
        _install(destination, installed)

    monkeypatch.setattr(build_tmux, "build", compile_fresh)
    assert build_tmux.prepare(prefix, ident)
    assert not prefix.is_symlink()
    assert original.read_bytes() == installed.read_bytes()


def test_failed_build_does_not_write_a_valid_cache_record(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject a compiler failure; a partial installation must remain invalid."""
    prefix = tmp_path / "tmux"

    def fail_build(destination: pathlib.Path, _: Identity) -> None:
        destination.mkdir()
        message = "compiler failed"
        raise RuntimeError(message)

    monkeypatch.setattr(build_tmux, "build", fail_build)
    with pytest.raises(RuntimeError, match="compiler failed"):
        build_tmux.prepare(prefix, {"version": "3.6"})
    assert not (prefix / "build.json").exists()


@pytest.mark.parametrize(
    "field",
    ["image", "arch", "source", "recipe", "compiler", "packages", "configure"],
)
def test_changed_build_environment_cannot_restore_the_same_key(field: str) -> None:
    """A source, recipe, toolchain, flag or runner change invalidates the binary."""
    ident = {
        "version": "3.6",
        "image": "ubuntu24-20260920.1",
        "arch": "x86_64",
        "source": "source-a",
        "recipe": "recipe-a",
        "compiler": "compiler-a",
        "packages": "packages-a",
        "configure": "",
    }
    changed = dict(ident)
    changed[field] += "-changed"
    assert build_tmux.cache_key(ident) != build_tmux.cache_key(changed)


@pytest.mark.parametrize("field", ["ImageOS", "ImageVersion"])
def test_missing_runner_image_is_rejected_before_source_resolution(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """An unbound runner variable must not produce another version-only key."""
    monkeypatch.setenv("ImageOS", "ubuntu26")
    monkeypatch.setenv("ImageVersion", "20261105.1")
    monkeypatch.setenv(field, "")
    with pytest.raises(ValueError, match="runner image"):
        build_tmux.identity("master")


def test_a_release_shaped_ref_without_a_pinned_checksum_is_refused() -> None:
    """Never build a release tag whose archive nothing verifies."""
    with pytest.raises(ValueError, match="no checksum"):
        build_tmux.source_of("9.9z")
    assert build_tmux.source_of("3.8") == build_tmux.RELEASES["3.8"]


def test_release_table_holds_checksums_for_release_names() -> None:
    assert build_tmux.RELEASES
    for release, checksum in build_tmux.RELEASES.items():
        assert re.fullmatch(r"\d+\.\d+[a-z]?", release)
        assert re.fullmatch(r"[0-9a-f]{64}", checksum)


def test_keyed_packages_cover_the_installed_build_dependencies() -> None:
    """A dependency whose version the key omits could serve a stale build."""
    meta = {"build-essential": {"gcc", "libc6"}}
    keyed = set(build_tmux.KEYED_PACKAGES)
    for package in build_tmux.BUILD_DEPENDENCIES:
        assert package in keyed or meta[package] <= keyed


def test_directory_names_cannot_collide_or_leave_the_runner_directory() -> None:
    """A branch with a slash gets one flat, distinct directory."""
    assert build_tmux.directory_name("3.8") == "tmux-3.8"
    names = {build_tmux.directory_name(ref) for ref in ("a/b", "a_b", "master")}
    assert len(names) == 3
    assert all("/" not in name for name in names)


_CONFIGURE = r"""#!/bin/sh
for argument in "$@"; do
	case $argument in --prefix=*) prefix=${argument#--prefix=} ;; esac
done
{
	printf 'PREFIX = %s\n' "$prefix"
	printf 'all:\n\t@true\n'
	printf 'install:\n\tmkdir -p $(PREFIX)/bin\n'
	printf '\techo "#!/bin/sh" > $(PREFIX)/bin/tmux\n'
	printf '\techo "echo tmux $$(cat VERSION)" >> $(PREFIX)/bin/tmux\n'
	printf '\tchmod +x $(PREFIX)/bin/tmux\n'
	printf '\techo "%s" > $(PREFIX)/configure-args\n' "$*"
} > Makefile
"""
_AUTOGEN = f"cat > configure <<'CONFIGURE'\n{_CONFIGURE}CONFIGURE\nchmod +x configure\n"


@pytest.fixture
def upstream(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Serve a repository shaped like tmux's: a tag, a branch and a master."""
    repository = tmp_path / "upstream"
    repository.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "tag.gpgsign=false",
                "-c",
                "init.defaultBranch=master",
                *args,
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=repository,
        ).stdout.strip()

    def commit(version: str) -> str:
        (repository / "VERSION").write_text(f"{version}\n")
        git("add", ".")
        git("commit", "--quiet", "--message", version)
        return git("rev-parse", "HEAD")

    git("init", "--quiet")
    (repository / "autogen.sh").write_text(_AUTOGEN)
    commits = {"tag": commit("tagged")}
    git("tag", "--annotate", "--message", "release", "9.9")
    git("branch", "feature/x")
    commits["master"] = commit("master")
    git("switch", "--quiet", "feature/x")
    commits["branch"] = commit("branch")
    git("switch", "--quiet", "master")
    git("config", "uploadpack.allowAnySHA1InWant", "true")
    monkeypatch.setattr(build_tmux, "REPOSITORY", f"file://{repository}")
    return commits


def test_every_kind_of_ref_resolves_to_its_commit(upstream: dict[str, str]) -> None:
    """An annotated tag resolves to the commit it tags, not the tag object."""
    for ref, commit in {
        "9.9": upstream["tag"],
        "master": upstream["master"],
        "feature/x": upstream["branch"],
        upstream["branch"]: upstream["branch"],
    }.items():
        assert build_tmux.resolve(ref) == commit


def test_unknown_ref_is_refused(upstream: dict[str, str]) -> None:
    """A name that no tag or branch carries must not become a cache key."""
    with pytest.raises(ValueError, match=r"no tag or branch named '9\.8'"):
        build_tmux.resolve("9.8")


@pytest.mark.parametrize("ref", ["9.9", "master", "feature/x", "branch-commit"])
def test_development_build_installs_the_commit_a_ref_names(
    tmp_path: pathlib.Path, upstream: dict[str, str], ref: str
) -> None:
    """Fetch the commit the identity resolved, and build exactly that."""
    if ref == "branch-commit":
        ref = upstream["branch"]
    commit = build_tmux.resolve(ref)
    prefix = tmp_path / "prefix"
    build_tmux.build(prefix, {"version": ref, "source": commit, "configure": ""})
    reported = subprocess.run(
        [str(prefix / "bin" / "tmux")], check=True, capture_output=True, text=True
    ).stdout.strip()
    names = {
        upstream["tag"]: "tagged",
        upstream["master"]: "master",
        upstream["branch"]: "branch",
    }
    assert reported == f"tmux {names[commit]}"


def test_configure_arguments_reach_configure_after_the_prefix(
    tmp_path: pathlib.Path, upstream: dict[str, str]
) -> None:
    prefix = tmp_path / "prefix"
    ident = {
        "version": "master",
        "source": upstream["master"],
        "configure": "--disable-utf8proc --with-x='a b'",
    }
    build_tmux.build(prefix, ident)
    arguments = (prefix / "configure-args").read_text().strip()
    assert arguments == f"--prefix={prefix} --disable-utf8proc --with-x=a b"


@pytest.fixture
def release_archive(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, str]:
    """Serve a release archive through a fake curl; return its version and SHA256."""
    version = "9.9z"
    archive = tmp_path / "served.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, text, mode in (
            (f"tmux-{version}/configure", _CONFIGURE, 0o755),
            (f"tmux-{version}/VERSION", f"{version}\n", 0o644),
        ):
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = mode
            tar.addfile(info, io.BytesIO(data))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(
        "#!/bin/sh\nwhile [ $# -gt 0 ]; do\n"
        f'  if [ "$1" = --output ]; then cp "{archive}" "$2"; fi\n  shift\ndone\n'
    )
    curl.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return version, hashlib.sha256(archive.read_bytes()).hexdigest()


def test_release_archive_must_match_its_pinned_checksum(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    release_archive: tuple[str, str],
) -> None:
    version, checksum = release_archive
    monkeypatch.setitem(build_tmux.RELEASES, version, checksum)
    prefix = tmp_path / "good"
    build_tmux.build(prefix, {"version": version, "source": checksum, "configure": ""})
    assert (prefix / "bin" / "tmux").is_file()

    monkeypatch.setitem(build_tmux.RELEASES, version, "0" * 64)
    with pytest.raises(ValueError, match="does not match its pinned SHA256"):
        build_tmux.build(
            tmp_path / "bad", {"version": version, "source": "0" * 64, "configure": ""}
        )
    assert not (tmp_path / "bad" / "bin" / "tmux").exists()


@NATIVE
def test_plan_and_prepare_publish_outputs_and_the_path(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    upstream: dict[str, str],
    native: tuple[pathlib.Path, Identity],
) -> None:
    """Drive the two phases the way the action does, with a stand-in compiler."""
    installed, _ = native
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    outputs, path = tmp_path / "output", tmp_path / "path"
    for name, value in {
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_OUTPUT": str(outputs),
        "GITHUB_PATH": str(path),
        "ImageOS": "ubuntu24",
        "ImageVersion": "20261105.1",
    }.items():
        monkeypatch.setenv(name, value)
    real_output = build_tmux.output
    monkeypatch.setattr(
        build_tmux,
        "output",
        lambda args: "fake" if args[0] in {"cc", "dpkg-query"} else real_output(args),
    )

    def compile_fresh(destination: pathlib.Path, _: Identity) -> None:
        _install(destination, installed)

    monkeypatch.setattr(build_tmux, "build", compile_fresh)
    flags = ["--configure-args=--disable-utf8proc"]
    assert build_tmux.main(["plan", "feature/x", *flags]) == 0
    written = dict(line.split("=", 1) for line in outputs.read_text().splitlines())
    prefix = pathlib.Path(written["prefix"])
    assert prefix.parent == runner_temp.resolve()
    assert written["binary"] == str(prefix / "bin" / "tmux")
    assert written["source"] == upstream["branch"]
    assert written["key"].startswith("tmux-v3-feature_x-")

    monkeypatch.setenv("CACHE_HIT", "false")
    assert build_tmux.main(["prepare", "feature/x", "--add-to-path"]) == 0
    assert (prefix / "build.json").is_file()
    assert path.read_text() == f"{prefix / 'bin'}\n"
    assert outputs.read_text().splitlines()[-1].startswith("version=")


def test_configure_arguments_cannot_move_the_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    with pytest.raises(ValueError, match="cannot set --prefix"):
        build_tmux.run_plan("3.8", None, "--prefix=/usr")


def test_dependencies_phase_prints_the_apt_package_list(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert build_tmux.main(["dependencies"]) == 0
    assert capsys.readouterr().out.split() == list(build_tmux.BUILD_DEPENDENCIES)
