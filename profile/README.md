<p align="center">
  <picture>
    <source srcset="https://raw.githubusercontent.com/libtmux/.github/main/assets/logo.svg" type="image/svg+xml">
    <img src="https://raw.githubusercontent.com/libtmux/.github/main/assets/logo.png" width="96" height="96" alt="libtmux">
  </picture>
</p>

# libtmux

`libtmux` provides typed client libraries for
[tmux](https://github.com/tmux/tmux),
[`tmuxp`](https://github.com/tmux-python/tmuxp)-compatible workspace loaders,
and Model Context Protocol (MCP) servers across languages, verified against
real tmux servers. Installation guides, examples, and cross-linked API
references are published together at [libtmux.org](https://libtmux.org/).

## Languages

| Language | Repository | Registry | Products | Documentation |
| --- | --- | --- | --- | --- |
| Python | [tmux-python/libtmux](https://github.com/tmux-python/libtmux), [tmuxp](https://github.com/tmux-python/tmuxp), [libtmux-mcp](https://github.com/tmux-python/libtmux-mcp) | [PyPI](https://pypi.org/project/libtmux/) ([tmuxp](https://pypi.org/project/tmuxp/), [libtmux-mcp](https://pypi.org/project/libtmux-mcp/)) | Library, Workspace, MCP | [libtmux.org/en/py/](https://libtmux.org/en/py/) |
| Rust | [libtmux/libtmux-rs](https://github.com/libtmux/libtmux-rs) | [crates.io](https://crates.io/crates/libtmux) | Library, Workspace, MCP | [libtmux.org/en/rs/](https://libtmux.org/en/rs/) |
| Go | [libtmux/libtmux-go](https://github.com/libtmux/libtmux-go) | [pkg.go.dev](https://pkg.go.dev/github.com/libtmux/libtmux-go/tmux) | Library, Workspace, MCP | [libtmux.org/en/go/](https://libtmux.org/en/go/) |
| TypeScript | [libtmux/libtmux-ts](https://github.com/libtmux/libtmux-ts) | [npm](https://www.npmjs.com/package/libtmux) | Library, Workspace, MCP | [libtmux.org/en/ts/](https://libtmux.org/en/ts/) |
| C++ | [libtmux/libtmux-cxx](https://github.com/libtmux/libtmux-cxx) | Source | Library, Workspace, MCP | [libtmux.org/en/cxx/](https://libtmux.org/en/cxx/) |
| Swift | [libtmux/libtmux-swift](https://github.com/libtmux/libtmux-swift) | [Swift Package Index](https://swiftpackageindex.com/libtmux/libtmux-swift) | Library, Workspace, MCP | [libtmux.org/en/swift/](https://libtmux.org/en/swift/) |
| Java | [libtmux/libtmux-java](https://github.com/libtmux/libtmux-java) | [Maven Central](https://central.sonatype.com/artifact/io.github.libtmux/libtmux) | Library, Workspace, MCP | [libtmux.org/en/java/](https://libtmux.org/en/java/) |
| Kotlin | [libtmux/libtmux-java](https://github.com/libtmux/libtmux-java) | [Maven Central](https://central.sonatype.com/artifact/io.github.libtmux/libtmux-kotlin) | Library (JVM companion) | [libtmux.org/en/kotlin/](https://libtmux.org/en/kotlin/) |
| Scala | [libtmux/libtmux-java](https://github.com/libtmux/libtmux-java) | [Maven Central](https://central.sonatype.com/artifact/io.github.libtmux/libtmux-scala_3) | Library (JVM companion) | [libtmux.org/en/scala/](https://libtmux.org/en/scala/) |
| Clojure | [libtmux/libtmux-java](https://github.com/libtmux/libtmux-java) | Source | Library (JVM companion) | [libtmux.org/en/clojure/](https://libtmux.org/en/clojure/) |
| .NET / C# | [libtmux/libtmux-dotnet](https://github.com/libtmux/libtmux-dotnet) | [NuGet](https://www.nuget.org/packages/LibTmux) | Library, Workspace, MCP | [libtmux.org/en/csharp/](https://libtmux.org/en/csharp/) |
| F# | [libtmux/libtmux-dotnet](https://github.com/libtmux/libtmux-dotnet) | [NuGet](https://www.nuget.org/packages/LibTmux.FSharp) | Library (.NET companion) | [libtmux.org/en/fsharp/](https://libtmux.org/en/fsharp/) |
| Ruby | [libtmux/libtmux-ruby](https://github.com/libtmux/libtmux-ruby) | [RubyGems](https://rubygems.org/gems/libtmux) | Library, Workspace, MCP | [libtmux.org/en/ruby/](https://libtmux.org/en/ruby/) |
| Lua | [libtmux/libtmux-lua](https://github.com/libtmux/libtmux-lua) | [LuaRocks](https://luarocks.org/modules/tony/libtmux) | Library | [libtmux.org/en/lua/](https://libtmux.org/en/lua/) |
| PowerShell | [libtmux/libtmux-powershell](https://github.com/libtmux/libtmux-powershell) | [PowerShell Gallery](https://www.powershellgallery.com/packages/LibTmux) | Library, Workspace | [libtmux.org/en/powershell/](https://libtmux.org/en/powershell/) |
| Julia | [libtmux/libtmux-julia](https://github.com/libtmux/libtmux-julia) | Source | Library, Workspace, MCP | [libtmux.org/en/julia/](https://libtmux.org/en/julia/) |
| Elixir | [libtmux/libtmux-elixir](https://github.com/libtmux/libtmux-elixir) | [Hex](https://hex.pm/packages/libtmux) | Library | [libtmux.org/en/elixir/](https://libtmux.org/en/elixir/) |
| Erlang | [libtmux/libtmux-erlang](https://github.com/libtmux/libtmux-erlang) | [Hex](https://hex.pm/packages/libtmux_erlang) | Library | [libtmux.org/en/erlang/](https://libtmux.org/en/erlang/) |
| Haskell | [libtmux/libtmux-haskell](https://github.com/libtmux/libtmux-haskell) | Source | Library | [libtmux.org/en/haskell/](https://libtmux.org/en/haskell/) |
| OCaml | [libtmux/libtmux-ocaml](https://github.com/libtmux/libtmux-ocaml) | Source | Library, Workspace | [libtmux.org/en/ocaml/](https://libtmux.org/en/ocaml/) |
| Common Lisp | [libtmux/libtmux-lisp](https://github.com/libtmux/libtmux-lisp) | Source | Library, Workspace | [libtmux.org/en/lisp/](https://libtmux.org/en/lisp/) |
| Perl | [libtmux/libtmux-perl](https://github.com/libtmux/libtmux-perl) | [MetaCPAN](https://metacpan.org/dist/LibTmux) | Library, Workspace | [libtmux.org/en/perl/](https://libtmux.org/en/perl/) |
| Raku | [libtmux/libtmux-raku](https://github.com/libtmux/libtmux-raku) | [Raku Land](https://raku.land/zef:libtmux/LibTmux) | Library | [libtmux.org/en/raku/](https://libtmux.org/en/raku/) |

## Shared repositories

| Repository | Purpose |
| --- | --- |
| [libtmux/docs](https://github.com/libtmux/docs) | Source for [libtmux.org](https://libtmux.org/): guides, examples, prompts, `llms.txt`, and API references |
| [libtmux/.github](https://github.com/libtmux/.github) | Organization community defaults (`SECURITY.md`, `AI_POLICY.md`, `WRITING.md`) and shared GitHub Actions |
| [tmux-python](https://github.com/tmux-python) | Organization hosting the Python [libtmux](https://github.com/tmux-python/libtmux), [tmuxp](https://github.com/tmux-python/tmuxp), and [libtmux-mcp](https://github.com/tmux-python/libtmux-mcp) packages |

Packages in `libtmux` are experimental unless a repository's `README` states
otherwise; pin exact versions and review changes before upgrading. Open an issue
in the relevant repository before preparing a pull request, and read the
[AI policy](https://github.com/libtmux/.github/blob/main/AI_POLICY.md) and
[libtmux/.github](https://github.com/libtmux/.github) for organization defaults.
