<h1 align="center">UniStudent</h1>

<p align="center"><strong>An AI plugin for university students.</strong><br>
Turn your course material into a per-course Wiki your AI is grounded in — every answer marked by where it came from — plus study packs for each unit.</p>

<p align="center">
  <a href="https://github.com/NoamTuriel/unistudent/actions/workflows/tests.yml"><img src="https://github.com/NoamTuriel/unistudent/actions/workflows/tests.yml/badge.svg" alt="tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-8b5cf6.svg" alt="license: MIT" /></a>
  <img src="https://img.shields.io/badge/MCP-compatible-38bdf8.svg" alt="MCP compatible" />
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB.svg" alt="python 3.9+" />
</p>

> A general AI answers from the whole internet: methods your course doesn't teach, other notation,
> material from other courses. Your exam grades your course's way. UniStudent keeps the AI inside your
> course material and tells you when it steps outside.

| Label | Meaning |
|:---:|---|
| ✅ | From your course material, with a link to the exact page or recording time |
| 💡 | The AI's own explanation of your course material (an example, an analogy, a memory trick), linked to what it explains |
| ⚠️ | Not in your course material |
| ❌ | Conflicts with how your course does it (the course version comes first) |

Works with Claude (Code, Desktop, Cowork), Cursor, VS Code, Codex, Gemini CLI and any other app that speaks MCP.

## What you get

| Piece | What it is | Where it works |
|---|---|---|
| **MCP server** `unistudent-mcp` | The tools: set up a course, add material, build and check the Wiki, study-pack bookkeeping, recordings | Any MCP app |
| **Skills** (Agent Skills format) | The step-by-step know-how: course-setup, course-add, course-wiki, study-pack, course-recordings, course-help, courses, openu-sync, economics, macro | Any app with skills; in other MCP apps the core skills appear as prompts |
| **Claude plugins** | All of the above plus subagents, installed in one step | Claude Code, Cowork |

| Plugin | What it does |
|---|---|
| `unistudent` | Core, any university: course folders, Wiki, recordings, study packs, grounding labels, preferences |
| `openu` | Open University of Israel: downloads new material from your course site |
| `economics` | Economics study-pack rules, and the intro macroeconomics course skill |

## Install

You need [uv](https://docs.astral.sh/uv/) (one installer; it fetches everything else) and, for recordings only, [ffmpeg](https://ffmpeg.org).

**Claude Code**

```
/plugin marketplace add NoamTuriel/unistudent
/plugin install unistudent@unistudent
/plugin install openu@unistudent        # Open University students
/plugin install economics@unistudent    # economics courses
```

**Claude Desktop, Cursor, VS Code, Windsurf**: add the MCP server to the app's MCP settings:

```json
{
  "mcpServers": {
    "unistudent": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent", "unistudent-mcp"]
    }
  }
}
```

(VS Code calls the top-level key `servers` and wants `"type": "stdio"`. Desktop apps on a Mac often can't see `uvx`: if the server doesn't start, put the full path from `which uvx` in `"command"`, e.g. `/Users/you/.local/bin/uvx`.)

**Codex CLI**: `codex mcp add unistudent -- uvx --from "git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent" unistudent-mcp`, or in `~/.codex/config.toml`:

```toml
[mcp_servers.unistudent]
command = "uvx"
args = ["--from", "git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent", "unistudent-mcp"]
```

**Gemini CLI**: the same `mcpServers` block as above, in `~/.gemini/settings.json`.

**Skills, for apps that support them** (Codex, Cursor, Gemini CLI, Claude and others): `npx skills@latest add NoamTuriel/unistudent` (it reads the skills declared in this repo's Claude plugin files). The skills do their work through the UniStudent MCP server, so add the server too; alternatively `uv tool install` below gives them the `unistudent` command.

Then, for each course, start the **course-setup** skill or prompt (`/unistudent:course-setup` in Claude Code). It first asks your university: if there's no installed plugin for it (like `openu` above), it interviews you once — course site URL, how you organize material — and remembers the answer, so the next course at the same university skips that question. Setup can be stopped and resumed at any point; running it again picks up where you left off.

Optional, for better results: `uv tool install "unistudent[all] @ git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent"` adds document converters (markitdown, pypdf, python-docx, python-pptx) and Hebrew speech-to-text (faster-whisper, or mlx-whisper on Apple silicon).

## Works well with

UniStudent uses existing tools instead of reinventing them:

- **[MarkItDown](https://github.com/microsoft/markitdown)** (Microsoft): converts Word, PowerPoint, Excel, HTML and EPUB files when installed. PDFs are converted page by page so answers can cite a page.
- **[ivrit.ai](https://huggingface.co/ivrit-ai) Whisper models**: Hebrew speech-to-text, run locally through faster-whisper or mlx-whisper.
- **[mcp-video-analyzer](https://github.com/guimatheus92/mcp-video-analyzer)**: add it next to UniStudent to let the AI look at the slides on screen while indexing a recording. Every transcript is also saved as WebVTT, which it (and video players) can use.
- **A browser tool** (Claude in Chrome, or a browser MCP server) for downloading from your course site with your own login.
- **[Obsidian](https://obsidian.md)**: study packs can use Obsidian links and callouts.

## Commands (skills)

| Skill | What it does |
|---|---|
| course-setup | Set up a course (once per course) |
| course-help | How it works, and what's waiting |
| course-add | Add what you dropped into the course's `inbox/` |
| course-wiki | Build or refresh the Wiki |
| study-pack | Build a study pack for a unit, or review proposed updates |
| course-recordings | Transcribe and summarise recordings (heavy; always asks first) |
| courses | List and switch courses |
| openu-sync | Download what's new on your OpenU course site |

## A course folder

```
<course>/
  AGENTS.md / CLAUDE.md   course context: grounding rules, exam facts, other courses
  README.md               how it works, for the student
  course-preferences.md
  inbox/                  drop new material here
  materials/              everything by unit (links, never copies)
  raw/                    every original file, once
  wiki/                   what the AI reads: sources, units, glossary, question bank, recordings
  study/                  your study packs
  .unistudent/            settings, manifest, full context
```

Each course has its own folder and its own Wiki. Open your AI app in the course folder (or, in Cowork, make one project per course with that folder connected) and it picks the course up automatically through `AGENTS.md`/`CLAUDE.md`. If a session isn't rooted in the folder (or doesn't auto-read it), tell it once: "Read AGENTS.md in `<course folder path>` before answering" — that works in any AI app, not just Claude's.

Course material is the university's: keep it in your own folders and never share it. The repo contains code only.

## Development

- Design: [`docs/spec/v1.md`](docs/spec/v1.md), vocabulary: [`CONTEXT.md`](CONTEXT.md), decisions: [`docs/adr/`](docs/adr/). Ticket history and dated project reviews are kept locally only (gitignored), not in this repo.
- One source of truth: the command line (`plugins/unistudent/scripts/unistudent/cli.py`, `commands.py`). The MCP server generates its tools from it.
- Tests: `python3 -m unittest discover -s tests` (standard library only; CI runs macOS, Windows and Linux on Python 3.9 and 3.12, with and without optional libraries).
- Grounding eval with a real model: `python3 evals/grounding/run.py` (needs the `claude` CLI).
