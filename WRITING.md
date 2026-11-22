# Writing

This guide governs the text in this repository and sets the shared writing
conventions across the [libtmux](https://github.com/libtmux) organization. A
port repository adds only language- or toolchain-specific rules in its own
`WRITING.md`. [AGENTS.md](AGENTS.md) owns how changes are made here.

## Voice

Lead with the result or the reader's task, and cut introductory sentences that
only announce what follows. Use active voice, present tense, concrete nouns,
and short declarative sentences. Put identifiers, flags, file paths, and
package names in backticks.

Describe observable behavior rather than restating types or signatures.
Replace vague adjectives ("robust", "comprehensive", "seamless", "optimized")
with the failure handled, the scope covered, or a measured result; omit filler
("easily", "simply", "just", "please note"), marketing claims, emojis, and
tool signatures.

Keep one domain noun per concept (`server`, `session`, `window`, `pane`,
`client`, `option`, `hook`, `buffer`). Write `tmux` in lowercase everywhere,
including at the start of a sentence. Use sentence-case headings. Assume no
shared conversation history: explain what a referenced issue, pull request, or
decision means, not just its identifier.

## Files GitHub shows elsewhere

A template or policy here is read inside other repositories. Write it so it
holds for every repository in the organization, and name a repository only when
the rule is about that repository. Link with absolute URLs.

## CommonMark

Use plain CommonMark in repository `.md` files, with blank lines around
headings, lists, and code blocks.

- **No GitHub-only alert blocks in repository `.md` files.** Do not use
  `> [!NOTE]`, `> [!WARNING]`, `> [!IMPORTANT]`, or other GitHub alert markers
  in tracked Markdown: package registries and external documentation renderers
  display those markers literally. Use a plain blockquote (`> ...`) or prose
  whose wording stands on its own.
- **Wrap repository `.md` prose near 80 columns.** Tables, badge rows, and
  lines dominated by a single long URL are exempt.
- **Never hard-wrap GitHub issue, pull request, or comment bodies.** GitHub
  renders single newlines in those bodies as line breaks rather than spaces, so
  write each prose paragraph on one line there.
- **Strip private and local details.** Exclude personal information, hostnames,
  and local absolute paths from published text.

## Code blocks

Treat command fences as paste-and-run units:

- Tag interactive shell commands `console` with a `$ ` prompt (`PS> ` for
  PowerShell).
- Put one paste-and-run command per fence. Combine multiple steps only when
  chained explicitly with `&&`, `;`, or `\` as one logical command.
- Split long commands with `\`, putting one flag or flag-and-value pair per
  indented continuation line and positional arguments last.
- Put explanations and prerequisites in prose above the fence, never as `#`
  comments inside it. Give each command in a menu its own prose lead-in and
  fence rather than a table.
- Keep displayed example code within 80 columns, enforced across ports by
  [check-example-width](actions/check-example-width/README.md).

Run the test suite on a single action directory:

```console
$ uv run \
    --group dev \
    pytest actions/check-example-width
```

## README shape

Package and port READMEs follow a shared shape (without hardcoded language,
file, or test counts in prose that drift as the project grows):

- **Header.** Open with the logo block (where used), title, badge row (CI,
  published registry version, [libtmux.org](https://libtmux.org/) docs when
  live, license; link only pages returning HTTP 200), and a concrete
  one-sentence summary before quickstart.
- **Tasks and linked APIs.** Make each `##` heading a task in the reader's
  words and each `###` heading a public API symbol in backticks, linked to its
  reference page, followed by its job in plain words.
- **Runnable, self-contained examples.** Keep paragraphs to three lines or
  fewer. Show capabilities through CI-executed examples that start with their
  imports and create and stop their own isolated `tmux` server through the
  library rather than shell `tmux` setup.
- **Actionable floors and closing sections.** State version requirements as
  floors (`tmux 3.3a or newer`), omit feature inventories and CI-matrix logs,
  list published packages with source, reference, registry, and changelog
  links, and close with short bullets for what the package leaves out and its
  support status.

Pre-1.0 ports (`0.1.N`) carry this plain CommonMark blockquote near the top of
the root `README.md`:

```markdown
> Releases are numbered `0.1.N`, and each release increments `N`. The API is
> not settled: any release may change or remove exported identifiers, and the
> changelog marks each break. Pin an exact version to avoid one.
```

## Source comments

A source comment ships only if it passes all three gates; delete or rewrite any
comment that fails or is borderline:

- **Loss.** Deleting it would cost a maintainer real time rediscovering an
  invariant, upstream `tmux` or platform quirk, protocol constraint, lifetime
  or concurrency rule, or why code that looks wrong is intentional.
- **Standard-library ceiling.** State only what the code and types cannot
  express, in one to three lines (four at most), without arguing with an
  imagined objector. Put rationale, tradeoffs weighed, and history in the
  commit message.
- **Upkeep.** The comment stays true without hand-syncing counts, line
  numbers, offsets, or constants owned by the code. Frozen external facts (such
  as a measured `tmux` release quirk) pass.

Delete line-by-line narration, restated identifiers or signatures, commented
code, tracker IDs without context, and transient wording ("currently", "for
now"). Public API docstrings and minimal caller examples are exempt from the
loss gate because they document caller contracts, while keeping the same
brevity and upkeep bar. Preserve compiler, linter, doctest, and snippet
directives that tooling reads.

## Slop prevention

Cut review-hostile filler and brittle metadata regardless of authorship:

- **No tool attribution or conversational padding.** Omit "Generated by"
  lines, AI co-author trailers, preamble or sign-off chatter, and emojis.
- **No brittle references.** Avoid hard-coded line numbers on moving branches,
  fragile file or test counts, dated "as of" claims, bare commit hashes, and
  local paths. Pin external source citations to a release tag or commit SHA.
- **No diff or branch diaries.** Code, docs, and pull request descriptions
  state the resulting behavior, not what moved, was renamed, or was tried on
  the branch. Mention old behavior only when users of a published release saw
  it.
- **No coded labels or speculative scaffolding.** Write rules in plain words
  rather than `[R1]` or `Option B`, and omit ownerless `TODO`s or guards for
  unreachable states.
- **Preserve the why.** Never delete a comment or note that documents an
  invariant, protocol rule, or upstream workaround just to shorten a file.

## Commits and pull requests

```text
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific changes made
- Focused on a single topic
```

The detail is optional. Keep subjects to 50 characters, excluding a trailing
`(#NN)`, and body lines to 72. Separate `why:` and `what:` with a blank line.
Use an imperative verb phrase, keep each commit to one topic, and do not use
Conventional Commits (`feat:`, `BREAKING CHANGE:`) footers. Release commits use
`Tag v<version>`, and only the maintainer creates or pushes release tags.

A pull request follows [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md) and
leads with the concrete problem and resulting behavior for a reader who has not
seen the conversation. Backtick every symbol, file path, command, flag, and
package name in both the title and body, list the checks run, and disclose tool
use per [AI_POLICY.md](AI_POLICY.md). Merge with a merge commit whose subject
ends in `(#NN)`, followed by `why:` and `what:` sections.
