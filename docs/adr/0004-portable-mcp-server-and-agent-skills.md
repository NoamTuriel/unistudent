# Portable by design: an MCP server generated from the CLI, and skills in the open Agent Skills format

Students use many AI apps, not only Claude. The core's commands are therefore exposed three ways from one source: the `unistudent` command line, an MCP server (`unistudent-mcp`) whose tools are generated from the command-line parser, and the same skills served as MCP prompts. Skills follow the open Agent Skills format (`SKILL.md`), avoid client-specific tool names through a shared conventions block, and have collision-safe names because many agents install skills into one flat folder. Claude-only extras (plugin marketplace, subagents, `disable-model-invocation`) are layered on top and ignored elsewhere.

## Considered options

- Claude plugin only: the simplest, but it locks out students on Cursor, VS Code, Codex or Gemini.
- A hand-written MCP server beside the CLI: two interfaces that drift apart. Generating one from the other keeps one source of truth.
- The official MCP Python SDK: better long-term, but it adds a dependency for a protocol subset (tools, prompts, stdio) that is small and stable. Revisit if the server needs resources, sampling or HTTP transport.
