# check-example-width

Fail a job when code a reader sees in rendered documentation is wider than 80
columns, and when the repository's example-width config or shared example rules
drift. Every libtmux port holds its examples to the same rules in `WRITING.md`,
and this action is the one copy of the checker that enforces them.

## Usage

```yaml
- uses: actions/checkout@<full-commit-sha>
  with:
    persist-credentials: false

- uses: libtmux/.github/actions/check-example-width@<full-commit-sha>
```

Pin the action to a full commit SHA. The job needs `git` and Python 3.11 or
later, which every hosted `ubuntu-24.04` runner has. The checker reads the files
git tracks, so it needs the checkout and no other step.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `root` | `.` | The repository to check: a path relative to the job's working directory, or absolute. |

The action has no outputs. It prints each wide line as `path:line: N columns > 80`
and, on a GitHub runner, adds an error annotation on that line.

## What it checks

The repository names what to read in `.github/example-width.toml`:

```toml
width = 80
tab_width = 4
markdown = ["**/*.md"]
sources = ["examples/**/*.ps1"]
doc_comments = ["src/**/*.cs"]
shared_digest = "<sha256 printed by --digest>"
allow_ceiling = 0

[[exclude]]
glob = "docs/reference/**"
reason = "generated command reference, not reader-facing examples"

[[allow]]
path = "README.md"
line = "the exact line, as it appears in the file"
reason = "why breaking it would make the example worse"
```

- Code in `markdown` files: fences, indented blocks outside lists, and `<pre>`
  blocks, plus literal and `code-block` blocks in a `.rst` file.
- Every line of `sources` files.
- Code in the doc comments of `doc_comments` files: fences, `>>>` doctests, and
  reST literal blocks in Python docstrings.
- Not output: `text` fences, and the lines a `console` block prints.
- A line that is only a URL, and a hidden line (a rustdoc `# ` line, a doctest
  marked `# doctest: +HIDE`), are skipped. Wide characters count as two columns.

The config itself is held to rules, so a mistake cannot weaken the check
silently: every key and glob must be known and match a tracked file, every
exclusion and allow entry needs a reason, `allow_ceiling` must equal the number
of allow entries, and every file under a directory named `examples` must be
checked or excluded.

It also checks the shared rules. `AGENTS.md` must link the section of
`WRITING.md` that holds the shared example rules. `WRITING.md`'s
`### In this repository` block must hold its four labelled bullets in order,
then one Bad and one Good example. The text between
`<!-- shared:examples -->` and `<!-- /shared:examples -->` must hash to
`shared_digest`, so an edit to that section in one port fails until every port
changes it together.

Run the helper from the repository to check, with `--digest`, to print the hash
to record. It takes the same pinned commit as the workflow:

```console
$ uv run https://raw.githubusercontent.com/libtmux/.github/<full-commit-sha>/actions/check-example-width/check_example_width.py --digest
```

## Development

The helper is `check_example_width.py`: typed Python for 3.11 and later,
standard library only. From the repository root:

```console
$ uv run --group dev pytest actions/check-example-width
```

The tests plant a wide line, a stale allow entry, a drifted shared section and
a broken config, and expect each to fail, beside a clean repository that must
pass. The `actions` workflow runs `ruff`, `ty`, `pytest` and the doctests on
every change, and runs the action itself on a clean and a wide repository.
