# AGENTS.md

Rules for this repository: the community health files of the
[libtmux](https://github.com/libtmux) organization. GitHub applies a file here
to every repository in the organization that has none of its own, so one change
here changes all of those repositories.

Follow the conventions already in the tree, and keep a change scoped to what
was asked for.

## What is here

Organization defaults that GitHub reads, and the policies they link to:

| Path | What it is |
| --- | --- |
| [SECURITY.md](SECURITY.md) | The security policy and private vulnerability reporting route of every repository without its own |
| [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md) | The pull request template of every repository without its own |
| [AI_POLICY.md](AI_POLICY.md) | How the libtmux and tmux-python projects treat AI tools, which the template links |
| [WRITING.md](WRITING.md) | Shared writing, CommonMark, README shape, comment, and commit conventions |
| [README.md](README.md) | What the repository is for |
| [actions/](actions/) | Composite actions the ports share, each with its README, tests and typed Python helper |
| [.github/workflows/actions.yml](.github/workflows/actions.yml) | Runs the checks and an integration build for those actions |

## Changing an action

A port pins an action by commit SHA, so a merged change reaches no port until
that port moves its pin. Keep an action's inputs and outputs stable, and say
in the commit when a change breaks a caller.

From the repository root, run the same checks as CI:

```console
$ uv run --group dev ruff format --check
```

```console
$ uv run --group dev ruff check
```

```console
$ uv run --group dev ty check
```

```console
$ uv run --group dev pytest
```

## Which policy applies

- Documentation, user-facing text, comments, and commit messages:
  [WRITING.md](WRITING.md)
- Use of AI tools, issues, and pull requests from contributors:
  [AI_POLICY.md](AI_POLICY.md)
- Vulnerability reporting, security scope, and supported versions:
  [SECURITY.md](SECURITY.md)

Each file is the single home for its subject.

## Change discipline

- Make the smallest coherent change that solves the verified problem.
- Check which repositories a change reaches before making it: a repository
  with its own copy of a file ignores the default here.
- Keep a rule that only one repository needs in that repository.
- Use absolute links in any file GitHub shows in another repository, such as a
  template. A relative link there resolves against that repository.
- Check that every link answers and every anchor exists before committing.

## References

- [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [libtmux.org](https://libtmux.org/), the documentation of every port
- [libtmux](https://libtmux.git-pull.com/), the Python library the ports
  build on
