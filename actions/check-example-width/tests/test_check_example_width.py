"""Tests for the example-width checker: planted failures and clean controls.

A check that cannot fail checks nothing, so each rule here has a case that must
be reported and a case that must pass.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import TYPE_CHECKING, Any

import check_example_width as cew
import pytest

if TYPE_CHECKING:
    import pathlib

WIDE = "let total = " + " + ".join(["value"] * 12) + ";"
BODY = "rule\n"
SHARED = f"<!-- shared:examples -->\n{BODY}<!-- /shared:examples -->\n"
PORT_LABELS = "\n".join(label + " x" for label in cew.PORT_LABELS)
PORT_BLOCK = f"### In this repository\n\n{PORT_LABELS}\n\nBad, over 80:\n\nGood, x:\n"


def git(root: pathlib.Path, *arguments: str) -> None:
    """Run git in a scratch repository."""
    subprocess.run(["git", "-C", str(root), *arguments], check=True)


def make_repo(root: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    """Write files, track them in a new repository, and return the root."""
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "init", "--quiet")
    git(root, "add", "--all")
    return root


def shared_digest_of(text: str) -> str:
    """Return the digest the config records for a shared section's body."""
    return hashlib.sha256(text.encode()).hexdigest()


def test_a_planted_wide_line_is_reported(tmp_path: pathlib.Path) -> None:
    (tmp_path / "README.md").write_text(f"```rust\n{WIDE}\n```\n")
    config: dict[str, Any] = {"width": 60, "markdown": ["README.md"]}
    findings, stale = cew.check(tmp_path, config, ["README.md"])
    assert [(f.path, f.number) for f in findings] == [("README.md", 2)]
    assert not stale


def test_an_allow_hint_round_trips_and_silences_the_line(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "README.md").write_text(f"```rust\n{WIDE}\n```\n")
    config: dict[str, Any] = {"width": 60, "markdown": ["README.md"]}
    (finding,) = cew.check(tmp_path, config, ["README.md"])[0]
    pasted = cew.tomllib.loads(cew.allow_hint(finding))["allow"][0]
    assert pasted["line"] == WIDE
    config["allow"] = [{"path": "README.md", "line": WIDE, "reason": "test"}]
    findings, stale = cew.check(tmp_path, config, ["README.md"])
    assert not findings
    assert not stale


def test_an_allow_entry_that_matches_no_line_is_stale(tmp_path: pathlib.Path) -> None:
    (tmp_path / "README.md").write_text(f"```rust\n{WIDE}\n```\n")
    config: dict[str, Any] = {
        "width": 60,
        "markdown": ["README.md"],
        "allow": [
            {"path": "README.md", "line": WIDE, "reason": "test"},
            {"path": "README.md", "line": "gone", "reason": "x"},
        ],
    }
    findings, stale = cew.check(tmp_path, config, ["README.md"])
    assert not findings
    assert [entry["line"] for entry in stale] == ["gone"]


def test_a_raw_tabbed_allow_entry_matches(tmp_path: pathlib.Path) -> None:
    tabbed = "\t" + WIDE
    (tmp_path / "main.go").write_text(tabbed + "\n")
    config: dict[str, Any] = {
        "width": 60,
        "sources": ["*.go"],
        "allow": [{"path": "main.go", "line": tabbed, "reason": "test"}],
    }
    findings, stale = cew.check(tmp_path, config, ["main.go"])
    assert not findings
    assert not stale


def test_formatter_copies_may_differ_only_on_the_width_key(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "fmt.toml").write_text("edition = 1\nmax_width = 100\n")
    (tmp_path / "copy.toml").write_text("edition = 1\nmax_width = 80\n")
    pair = {"copy": "copy.toml", "root": "fmt.toml", "key": "max_width"}
    copies = {"formatter_copies": [pair]}
    assert not cew.copy_problems(tmp_path, copies)
    (tmp_path / "copy.toml").write_text("edition = 2\nmax_width = 80\n")
    assert cew.copy_problems(tmp_path, copies)
    absent = {"copy": "gone.toml", "root": "fmt.toml", "key": "max_width"}
    assert cew.copy_problems(tmp_path, {"formatter_copies": [absent]})


def test_the_shared_section_digest_is_checked(tmp_path: pathlib.Path) -> None:
    assert cew.shared_digest(tmp_path) == "missing"
    (tmp_path / "WRITING.md").write_text(SHARED)
    body = "rule\n"
    assert cew.shared_digest(tmp_path) == shared_digest_of(body)
    assert not cew.digest_problems(tmp_path, {"shared_digest": shared_digest_of(body)})
    (changed,) = cew.digest_problems(tmp_path, {"shared_digest": "0" * 64})
    assert changed.startswith("WRITING.md: the shared section has digest")
    (absent,) = cew.digest_problems(tmp_path, {})
    assert "shared_digest is missing" in absent


def test_agents_md_must_link_the_section_with_the_example_rules(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "WRITING.md").write_text("## Examples\n\n" + SHARED)
    assert cew.routing_problems(tmp_path), "a missing AGENTS.md passed"
    agents = tmp_path / "AGENTS.md"
    agents.write_text("Code examples: WRITING.md#examples\n")
    assert cew.routing_problems(tmp_path), "a bare anchor counted as a link"
    agents.write_text("[Examples](docs/WRITING.md#examples)\n")
    assert cew.routing_problems(tmp_path), "a link to a missing file passed"
    agents.write_text("[Examples](WRITING.md#examples)\n")
    assert not cew.routing_problems(tmp_path)


def test_a_comment_in_a_fence_is_not_a_heading(tmp_path: pathlib.Path) -> None:
    fenced = "## Examples\n\n```sh\n# a comment\n```\n\n" + SHARED
    (tmp_path / "WRITING.md").write_text(fenced)
    (tmp_path / "AGENTS.md").write_text("[Examples](WRITING.md#examples)\n")
    assert not cew.routing_problems(tmp_path)


def test_the_port_block_needs_every_label_in_order() -> None:
    assert not cew.port_block_problems(PORT_BLOCK)
    missing = PORT_BLOCK.replace(cew.PORT_LABELS[2], "- **Other:**")
    assert cew.port_block_problems(missing)
    assert cew.port_block_problems("## Examples\n") == [
        'no "### In this repository" block'
    ]


def test_a_key_nested_under_a_table_header_is_reported() -> None:
    nested = cew.tomllib.loads(
        'allow_ceiling = 0\n[[exclude]]\nglob = "a"\nreason = "r"\n'
        'doc_comments = ["a"]\n'
    )
    nested["markdown"] = ["a"]
    assert any("doc_comments" in p for p in cew.config_problems(nested, ["a"]))
    del nested["exclude"][0]["doc_comments"]
    assert not cew.config_problems(nested, ["a"])


def test_a_checker_digest_is_no_longer_a_config_key() -> None:
    config = {"checker_digest": "0" * 64, "allow_ceiling": 0}
    (problem,) = cew.config_problems(config, [])
    assert problem.startswith("unknown key: checker_digest")


def test_values_of_the_wrong_type_are_reported() -> None:
    typed = {"width": "80", "markdown": "**/*.md"}
    assert len(cew.type_problems(typed)) == 2
    listed = {"allow": [{"path": ["a"], "line": "b", "reason": "c"}]}
    assert cew.type_problems(listed)
    assert not cew.type_problems({"width": 80, "markdown": ["a"]})


def test_an_entry_missing_a_key_is_reported_and_never_crashes(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "README.md").write_text(f"```rust\n{WIDE}\n```\n")
    misnamed: dict[str, Any] = {
        "markdown": ["README.md"],
        "exclude": [{"path": "README.md", "reason": "r"}],
        "allow": [{"file": "README.md", "line": WIDE, "reason": "r"}],
        "formatter_copies": [{"copy": "copy.toml", "root": "fmt.toml"}],
        "allow_ceiling": 1,
    }
    found = " ".join(cew.config_problems(misnamed, ["README.md"]))
    assert all(f"has no {key}" in found for key in ("glob", "path", "key"))
    cew.check(tmp_path, misnamed, ["README.md"])
    cew.copy_problems(tmp_path, misnamed)


def test_the_allow_ceiling_must_equal_the_allow_entries() -> None:
    entry = {"path": "a", "line": "b", "reason": "c"}
    grown: dict[str, Any] = {"allow": [entry, entry], "allow_ceiling": 1}
    assert cew.config_problems(grown, ["a"])
    shrunk: dict[str, Any] = {"allow": [entry], "allow_ceiling": 2}
    assert cew.config_problems(shrunk, ["a"])
    exact: dict[str, Any] = {"allow": [entry], "allow_ceiling": 1}
    assert not cew.config_problems(exact, ["a"])


def run_main(
    root: pathlib.Path, capsys: pytest.CaptureFixture[str], *arguments: str
) -> tuple[int, str]:
    """Run the command line against a repository and return status and output."""
    status = cew.main(["--root", str(root), *arguments])
    return status, capsys.readouterr().out


CONFIG = 'width = 80\nmarkdown = ["**/*.md"]\nallow_ceiling = 0\n'
NO_SECTION = CONFIG + 'shared_digest = "missing"\n'


def test_a_clean_repository_passes(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_repo(
        tmp_path,
        {".github/example-width.toml": NO_SECTION, "README.md": "```sh\nls\n```\n"},
    )
    status, output = run_main(root, capsys)
    assert status == 0
    assert output == "1 files checked; no example is over 80.\n"


def test_a_wide_example_fails_the_command_line(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    root = make_repo(
        tmp_path,
        {
            ".github/example-width.toml": NO_SECTION,
            "README.md": f"Intro.\n\n```rust\n{WIDE}\n```\n",
        },
    )
    status, output = run_main(root, capsys)
    assert status == 1
    assert f"README.md:4: {cew.columns(WIDE)} columns > 80" in output
    assert f"::error file=README.md,line=4::{cew.columns(WIDE)} columns > 80" in output
    assert "1 wide line" in output
    assert "[[allow]]" in output


def test_a_stale_allow_entry_fails_the_command_line(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = (
        'markdown = ["**/*.md"]\nallow_ceiling = 1\n\n[[allow]]\n'
        'path = "README.md"\nline = "gone"\nreason = "r"\n'
    )
    root = make_repo(
        tmp_path,
        {".github/example-width.toml": config, "README.md": "```sh\nls\n```\n"},
    )
    status, output = run_main(root, capsys)
    assert status == 1
    assert "allow entry for README.md matches no line: 'gone'" in output


def test_a_config_that_cannot_be_read_fails_the_command_line(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_repo(tmp_path, {"README.md": "ls\n"})
    status, output = run_main(root, capsys)
    assert status == 1
    assert "cannot read the config" in output


def test_a_changed_shared_section_fails_the_command_line(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = CONFIG + f'shared_digest = "{shared_digest_of(BODY)}"\n'
    files = {
        ".github/example-width.toml": config,
        ".github/WRITING.md": "## Examples\n\n" + SHARED + "\n" + PORT_BLOCK,
        "AGENTS.md": "[Examples](.github/WRITING.md#examples)\n",
    }
    root = make_repo(tmp_path, files)
    status, _ = run_main(root, capsys)
    assert status == 0
    edited = files[".github/WRITING.md"].replace("rule", "other rule")
    (root / ".github/WRITING.md").write_text(edited)
    status, output = run_main(root, capsys)
    assert status == 1
    assert "the shared section has digest" in output


def test_digest_prints_the_shared_section_digest(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_repo(tmp_path, {"WRITING.md": SHARED})
    status, output = run_main(root, capsys, "--digest")
    assert status == 0
    assert output == f"shared {shared_digest_of(BODY)}\n"


def test_the_helper_reports_its_own_documentation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as stopped:
        cew.main(["--help"])
    assert stopped.value.code == 0
    assert json.dumps(capsys.readouterr().out).startswith('"usage:')
