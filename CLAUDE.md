# Working on this repo

- Use the vocabulary in `CONTEXT.md` in code, tests, skills and docs. Respect the decisions in `docs/adr/`.
- Tests: `python3 -m unittest discover -s tests`. Write tests only at the three seams (sync, Wiki build, grounding), through the `us.py` command line.
- Scripts: Python standard library only; optional libraries behind `try/except ImportError`. OS-specific behaviour lives in `links.py` and `recordings.py` only.
- The CLI (`cli.py`, `commands.py`) is the single source of truth: the MCP server generates its tools from the argument parser, so a new command or option is automatically a tool.
- Core skills share one conventions block (`us` / delegate / ask); `tests/test_skills.py` keeps it identical. Use existing tools before writing new ones (markitdown, ffmpeg, faster-whisper / mlx-whisper, mcp-video-analyzer).
- Skills and agents follow `writing-for-agents`: steps with "Done when" criteria, one source of truth per rule. The grounding rule's single source is `plugins/unistudent/scripts/unistudent/templates/context.md`; study-pack generic rules live in `plugins/unistudent/scripts/unistudent/reference/study-pack.md`.
- Subject plugins never depend on a university plugin; university plugins never hold study-pack rules.
- Never commit course material.
