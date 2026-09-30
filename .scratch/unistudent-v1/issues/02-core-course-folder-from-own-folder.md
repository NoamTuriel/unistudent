# 02: Core first working version: course folder from the student's own folder

**What to build:** The repo exists as a marketplace with three plugins (core, openu, economics; the last two empty). In core-only mode, `/setup` points at a folder the student already has and creates a course folder: Settings, a Registry entry, Raw with a Manifest, a short course context file and a README. Imported files stay where they are; the human-readable layout is built from links, on macOS, Windows and Linux. Nothing is copied.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Repo installs as a marketplace in Claude Code and Cowork; all three plugins appear
- [ ] `/setup` (core-only) creates a course folder from an existing folder and registers it in the Registry
- [ ] Every imported file appears once in the Manifest with origin "student folder" and its original path; no file is duplicated on disk
- [ ] The readable layout uses symlinks on macOS/Linux and hard links/junctions on Windows without admin rights; falls back to an index page when links can't be made
- [ ] Scripts are Python only and pass the same tests on macOS, Windows and Linux (CI matrix)
- [ ] Re-running setup on the same folder is idempotent
