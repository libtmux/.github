# libtmux organization defaults

GitHub reads the community health files here for every repository in the
[libtmux](https://github.com/libtmux) organization that does not carry its own.

| File | What it covers |
| --- | --- |
| [profile/README.md](profile/README.md) | Public profile rendered on [github.com/libtmux](https://github.com/libtmux) |
| [SECURITY.md](SECURITY.md) | Private vulnerability reporting, supported versions, and security scope |
| [AI_POLICY.md](AI_POLICY.md) | Using AI tools with these packages and contributing issues or pull requests |
| [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md) | Default pull request template linking the AI policy |
| [WRITING.md](WRITING.md) | Shared writing, CommonMark, README shape, comment, and commit conventions |

The repository also hosts composite actions the ports share, so each fix lands
once. A workflow uses one as `libtmux/.github/actions/<name>@<full-commit-sha>`.

| Action | What it does |
| --- | --- |
| [apt-get](actions/apt-get/README.md) | Runs `apt-get` under a timeout and rotates the mirror when one hangs |
| [build-tmux](actions/build-tmux/README.md) | Builds, caches and validates a tmux from a release, tag, branch or commit |
| [check-example-width](actions/check-example-width/README.md) | Fails when documentation examples are wider than 80 columns or the shared example rules drift |
