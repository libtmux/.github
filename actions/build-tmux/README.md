# build-tmux

Build a private tmux from a release, tag, branch or commit of
[tmux/tmux](https://github.com/tmux/tmux), cache it, and output the path of the
binary. A cached build is validated before it is used, and rebuilt when it is
rejected.

## Usage

```yaml
- name: Build tmux 3.8
  id: tmux
  uses: libtmux/.github/actions/build-tmux@<full-commit-sha>
  with:
    ref: "3.8"

- run: ${{ steps.tmux.outputs.binary }} -V
```

Pin the action to a full commit SHA. A job can build several tmux versions: each
gets its own prefix, and none is put on `PATH` unless `add-to-path` asks for it.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `ref` | required | A release in [`tmux-releases.json`](tmux-releases.json), or a tag, branch or 40-hex commit of tmux/tmux. |
| `prefix` | a directory in `RUNNER_TEMP` | Install tmux under this directory. |
| `configure-args` | empty | Extra arguments for `./configure`, split like a shell command line, such as `--disable-utf8proc`. They are part of the cache key. `--prefix` is refused; use `prefix`. |
| `add-to-path` | `false` | Add the install's `bin` directory to `PATH` for the later steps of the job. |

## Outputs

| Output | Meaning |
| --- | --- |
| `binary` | The absolute path of the tmux executable. |
| `prefix` | The install prefix; `bin/tmux` is the executable. |
| `version` | The version the executable reports, such as `3.3a`. |
| `source` | The SHA256 of the release archive, or the commit a ref resolved to. |
| `cache-key` | The cache key. |
| `cache-hit` | `true` when an exact cache entry was restored, before validation. |

## What it does

1. Installs the build and runtime dependencies through the
   [apt-get action](../apt-get/README.md) in this repository. It does so on a
   cache hit too: a restored tmux links the libraries of the image.
2. Identifies the source and the build environment, and prints both.
3. Restores the cache entry for that identity.
4. Validates the restored build, or builds one when none is restored or the
   build is rejected.
5. Saves a validated build that was not restored.

### Source

A release in `tmux-releases.json` is built from its official archive. The action
checks the archive against the SHA256 pinned there and fails when they differ.

Any other ref resolves once, in step 2, to a commit: an annotated tag to the
commit it tags, a branch to its tip, a full commit to itself. The action fetches
exactly that commit, so a branch moving between steps cannot change the build.
It then runs `autogen.sh`.

A ref shaped like a release, such as `3.9`, that has no pin is an error. It is
never built from a tag without a checksum.

### Cache identity

The cache key names everything the build depends on: the ref, the source, the
runner image and its version, the architecture, the compiler, the versions of
the build packages, the `configure` arguments and a digest of `build_tmux.py`.
The runner image comes from the runner's `ImageOS` and `ImageVersion`
variables, so a self-hosted runner without them fails.

Never add a broad `restore-keys` fallback for a native binary. GitHub caches
are immutable: repairing an invalid exact hit fixes the current job and cannot
overwrite the entry, so a change to `build_tmux.py` is what invalidates it for
later jobs.

### Validation

A restored build is used only when all of these hold:

- the prefix, `bin` and `tmux` are not symbolic links;
- `build.json` records this identity and the SHA256 of the executable;
- `tmux -V` reports the requested release;
- a private daemon starts, answers with the same version, and shuts down.

A build that fails any check is deleted and rebuilt, and the job warns when an
exact cache hit was rebuilt.

## Releases the table pins

Run `python3 -c 'import json; print(*json.load(open("tmux-releases.json")))'`
for the list. To pin a new release, download its archive from
[tmux/tmux releases](https://github.com/tmux/tmux/releases), compute the SHA256,
compare it with the release asset's `digest` where GitHub shows one, and add the
entry to `tmux-releases.json`. The helper does not change.

## Development

The helper is `build_tmux.py`: typed Python for 3.10 and later, standard
library only, so it runs on every hosted Ubuntu image. From the repository root:

```console
$ uv run --group dev pytest actions/build-tmux
```

Tests marked `native` start a real tmux, the one on `PATH` or the one in
`TMUX_BINARY`. The `actions` workflow runs `ruff`, `ty`, `pytest` and the
doctests, then builds tmux 3.3a and 3.8 with the action and runs the native
tests against each build.
