# apt-get

Run `apt-get` on a GitHub-hosted runner without letting one hung mirror stall
the job.

On ubuntu-24.04 images 20260927, 20261004 and 20261012, `apt-get update`
sometimes ignores the Azure mirror and falls back to
`https://archive.ubuntu.com/ubuntu`, then hangs until the job timeout. The
image's 15 second `Acquire` timeout does not apply after the failover. See
[actions/runner-images#15040](https://github.com/actions/runner-images/issues/15040).

The action runs `apt-get -o Acquire::Retries=3 <args>` as root under `timeout`.
When an attempt fails or times out, it moves the first line of
`/etc/apt/apt-mirrors.txt` to the end, so the next attempt starts on another
mirror, and tries again. Three attempts run in all, and the step fails when the
last one does.

## Usage

```yaml
- uses: libtmux/.github/actions/apt-get@<full-commit-sha>
  with:
    update: "true"
    args: install --yes --no-install-recommends libevent-dev
```

Pin the action to a full commit SHA.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `args` | required | The `apt-get` arguments, split like a shell command line. |
| `timeout` | `180` | Seconds one attempt may take before `timeout` kills it. |
| `update` | `false` | Run `apt-get update` first, under the same timeout and rotation. |

The action has no outputs. A job that needs `apt-get update` and
`apt-get install` runs one step with `update: "true"`, not two steps.

## Behavior notes

- The command runs through `sudo`, unless the job already runs as root.
- `--kill-after=10` follows the timeout, so an `apt-get` that ignores `SIGTERM`
  still dies.
- The mirror list is rotated only between attempts, and only when the file
  exists and is not empty.

## Development

The helper is `apt_get.py`, typed Python with no dependencies outside the
standard library. From the repository root:

```console
$ uv run --group dev pytest actions/apt-get
```

The repository's `actions` workflow runs `ruff`, `ty`, `pytest` and the
doctests on every change.
