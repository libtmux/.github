# Security policy

This policy applies to repositories in the
[libtmux](https://github.com/libtmux) organization that do not carry their own
`SECURITY.md`.

## Reporting a vulnerability

Report suspected vulnerabilities privately rather than in a public issue,
discussion, or pull request. Open the affected repository on
[github.com/libtmux](https://github.com/libtmux), go to its **Security** tab,
and choose **Report a vulnerability** to open a private security advisory.

Include the package and version, your platform and `tmux` version, what you
observed, and a minimal reproduction or code reference. Distinguish verified
behavior from suspected impact, and coordinate disclosure so a fix can ship
before details become public.

## Supported versions

Pre-1.0 and `0.1.N` packages support only the latest published release.
Security fixes ship as a new release rather than as backports to older
versions. Published releases remain on package registries unpatched, so pin
deliberately and upgrade to receive fixes.

## What is in scope

Libraries and tools in `libtmux` build `tmux` argument vectors, speak control
mode, manage sockets, and parse `tmux` output. Vulnerabilities cross one of
those boundaries:

- **Argument or framing injection.** Input passed through a typed API (such as
  a session, window, or pane name, target, option value, or library-composed
  format string) that escapes its `tmux` `argv` slot, injects an extra `tmux`
  command or control-mode frame, or triggers unintended `#(...)` format
  command expansion.
- **Parser hangs or crashes on malformed output.** Output from `tmux`, or from
  a process on the other end of a transport, that causes a parser to hang,
  crash, exhaust memory, or corrupt state instead of returning an error.
- **Unintended socket or server selection.** Reaching a `tmux` socket or
  server other than the endpoint the caller configured, or leaking a socket
  across an isolation boundary.

## What is out of scope

- **Vulnerabilities in `tmux` itself.** Report defects in the `tmux` server or
  client binary upstream at [tmux/tmux](https://github.com/tmux/tmux).
- **Commands or shell strings a caller explicitly passes.** Sending keys to a
  pane or passing caller-supplied strings to `new-session`, `new-window`,
  `split-window`, `send-keys`, `run-shell`, `if-shell`, `pipe-pane`, raw
  command APIs, or hooks executes what the caller asked `tmux` or the shell to
  run. Callers passing untrusted input to those surfaces own that boundary.
- **Trusted `command-alias` server configuration.** `tmux` expands server
  `command-alias` entries before resolving built-in command names, so typed
  library guarantees assume trusted server configuration rather than aliases
  that redefine built-in `tmux` commands.
- **Documented MCP server terminal actions.** The MCP servers exist to read
  panes, send input, and run documented `tmux` operations on the endpoint they
  were given. Point an MCP server only at a dedicated `tmux` socket or server
  you intend that client to drive.
