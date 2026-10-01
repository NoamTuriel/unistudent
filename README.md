<p align="center">
  <img src="assets/icon.svg" width="96" height="96" alt="UniStudent" />
</p>

<h1 align="center">UniStudent</h1>

<p align="center"><strong>An AI plugin for university students.</strong><br>
It builds a Wiki out of your course's own files, so the AI answers from what your course teaches and nothing else.</p>

<p align="center">
  <a href="https://github.com/NoamTuriel/unistudent/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/NoamTuriel/unistudent/tests.yml?branch=main&label=tested&logo=github&logoColor=white" alt="tested" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-8b5cf6.svg" alt="license: MIT" /></a>
  <img src="https://img.shields.io/badge/MCP-compatible-38bdf8.svg" alt="MCP compatible" />
</p>

## How it works

1. **Collect.** It pulls your course material into one course folder, sorted by trust level and unit. That can come from your university's site or from files you already have: slides, books, past exams, recordings.
2. **Read.** It reads and transcribes all of it and writes the Wiki: a set of Markdown files that only the AI reads, made from your course and nothing else.

## What you can do with the Wiki

- **Get study packs.** For each unit you get a roadmap of what to memorize and what to understand, a map of the exercise types, and a plain explanation of each concept, with the graphs the course uses redrawn. They are generated as soon as the Wiki exists.
- **Find things in recordings.** Each recording gets a summary that says when a topic is explained, when an example is worked through, and when the lecturer announces something (a deadline, a change, "this will be on the exam"), with the time so you can jump there.
- **Ask questions about your course.** The answer comes from your course material, not from the wider internet.

> A general AI answers from the whole internet: methods your course doesn't teach, other notation,
> material from other courses. Your exam grades your course's way. UniStudent keeps the AI inside your
> course material and tells you when it steps outside.

| Label | Meaning |
|:---:|---|
| ✅ | From your course material, with a link to the exact page or recording time |
| 💡 | The AI's own explanation of your course material (an example, an analogy, a memory trick), linked to what it explains |
| ⚠️ | Not in your course material |
| ❌ | Conflicts with how your course does it (the course version comes first) |

Here is what the labels look like. This is a made-up example for an intro to economics course, not a real transcript:

> **Q: Why does the demand curve slope down?**
>
> ✅ As the price rises, buyers purchase less of the good (Unit 2, p. 14).
>
> 💡 Think of coffee: if a cup goes from 10 to 20 shekels, you start making it at home. That is the substitution effect from the same page, in an everyday case.
>
> ⚠️ Behavioral economists also explain this through loss aversion. Your course material doesn't cover that.

Works with Claude (Code, Desktop, Cowork), Cursor, VS Code, Codex, Gemini CLI and any other app that speaks MCP.

## What's in the box

There are three pieces. The **MCP server** (`unistudent-mcp`) holds the tools: set up a course, add material, build and check the Wiki, keep track of study packs, process recordings. It works in any MCP app. The **skills** (Agent Skills format) are the step-by-step instructions that use those tools; apps with skill support load them directly, and other MCP apps show the core skills as prompts. The **Claude plugins** bundle both with some subagents and install in one step in Claude Code and Cowork.

The skills are split across three plugins. `unistudent` is the core and works for any university. `openu` is for the Open University of Israel and downloads new material from your course site. `economics` holds study-pack rules for economics courses, plus a skill for the intro macroeconomics course.

| Skill | Plugin | What it does |
|---|---|---|
| course-setup | `unistudent` | Set up a course (once per course) |
| course-help | `unistudent` | How it works, and what's waiting |
| course-add | `unistudent` | Move what you dropped into the course's inbox into the Material folder and add it to the Wiki |
| course-wiki | `unistudent` | Build or refresh the Wiki |
| study-pack | `unistudent` | Build a study pack for a unit, or review proposed updates |
| course-recordings | `unistudent` | Transcribe and summarise recordings (heavy; always asks first) |
| courses | `unistudent` | List and switch courses |
| openu-sync | `openu` | Download what's new on your OpenU course site |
| economics, macro | `economics` | Study-pack rules for economics courses; the intro macroeconomics course skill |

## Install

You need [uv](https://docs.astral.sh/uv/) (one installer; it fetches everything else) and, for recordings only, [ffmpeg](https://ffmpeg.org). On a Mac, the `uv` installer may leave `uvx` off the PATH that apps see (zsh doesn't read the file it edits): add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshenv`, restart the app, and in a desktop app's MCP settings use the full path from `which uvx`.

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
      "args": ["--from", "git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent", "--with", "matplotlib", "unistudent-mcp"]
    }
  }
}
```

(VS Code calls the top-level key `servers` and wants `"type": "stdio"`. Desktop apps on a Mac often can't see `uvx`: if the server doesn't start, put the full path from `which uvx` in `"command"`, e.g. `/Users/you/.local/bin/uvx`.)

**Codex CLI**: `codex mcp add unistudent -- uvx --from "git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent" --with matplotlib unistudent-mcp`, or in `~/.codex/config.toml`:

```toml
[mcp_servers.unistudent]
command = "uvx"
args = ["--from", "git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent", "--with", "matplotlib", "unistudent-mcp"]
```

**Gemini CLI**: the same `mcpServers` block as above, in `~/.gemini/settings.json`.

**Skills, for apps that support them** (Codex, Cursor, Gemini CLI, Claude and others): `npx skills@latest add NoamTuriel/unistudent` (it reads the skills declared in this repo's Claude plugin files). The skills do their work through the UniStudent MCP server, so add the server too; alternatively `uv tool install` below gives them the `unistudent` command.

Then, for each course, start the **course-setup** skill or prompt (`/unistudent:course-setup` in Claude Code). It first asks your university, and once it knows your university and course it tells you which of the plugins above to install, with the exact command (so you only need `unistudent` to start). If there's no installed plugin for it (like `openu` above), it interviews you once — course site URL, how you organize material — and remembers the answer, so the next course at the same university skips that question. Setup can be stopped and resumed at any point; running it again picks up where you left off.

Optional, for better results: `uv tool install "unistudent[all] @ git+https://github.com/NoamTuriel/unistudent#subdirectory=plugins/unistudent"` adds document converters (markitdown, pypdf, python-docx, python-pptx), Hebrew speech-to-text (faster-whisper, or mlx-whisper on Apple silicon) and matplotlib for the graphs in study packs. (The plugin and the `uvx` setups above already include matplotlib.)

## Works well with

UniStudent uses existing tools instead of reinventing them:

- **[MarkItDown](https://github.com/microsoft/markitdown)** (Microsoft): converts Word, PowerPoint, Excel, HTML and EPUB files when installed. PDFs are converted page by page so answers can cite a page.
- **[ivrit.ai](https://huggingface.co/ivrit-ai) Whisper models**: Hebrew speech-to-text, run locally through faster-whisper or mlx-whisper.
- **[mcp-video-analyzer](https://github.com/guimatheus92/mcp-video-analyzer)**: add it next to UniStudent to let the AI look at the slides on screen while indexing a recording. Every transcript is also saved as WebVTT, which it (and video players) can use.
- **A browser tool** (Claude in Chrome, or a browser MCP server) for downloading from your course site with your own login.
- **[Obsidian](https://obsidian.md)**: the best way to read the Wiki and study packs (links between pages, callouts). Setup also offers Word, OneNote and Google Docs: the packs stay Markdown and you copy a finished pack into them.

## A course folder

You see three folders, numbered in the order you use them, named in the language you pick in setup (shown here in English; Hebrew has its own names, other languages fall back to English):

```
<course>/
  AGENTS.md / CLAUDE.md          course context: grounding rules, exam facts, other courses
  README.md                      how it works, for the student
  course-preferences.md
  1-inbox/                       drop new material here; it is moved out once it's added
  2-course-material/             the real files: official/ and added/, then by unit
  3-<course>-study-from-here/    your Study vault: study packs and a recordings roadmap per unit
  .unistudent/                   hidden: settings, manifest, the Wiki the AI reads, jobs, saved state
```

Open the third folder as your vault (in Obsidian or any other app). In the second you may move, rename or delete files: where a file sits is what counts (moving one between `official/` and `added/` changes how far it is trusted), and the next Wiki build follows. Deleting there deletes the only copy (your system Trash can recover it). A folder of your own is copied in once and your originals are left alone. A course folder made by an earlier version (with `raw/`, `materials/`, `wiki/`, `study/`) keeps working, and `us migrate` shows what it will move and then moves it.

Each course has its own folder and its own Wiki. Open your AI app in the course folder (or, in Cowork, make one project per course with that folder connected) and it picks the course up automatically through `AGENTS.md`/`CLAUDE.md`. Claude Code, Cursor, Codex and Gemini CLI read the folder's instruction files on their own (VS Code Copilot does too once its `AGENTS.md` setting is on). Claude Desktop chat reads no folder: create a Project once with the instruction "Start each chat by calling the unistudent `course_context` tool" and every chat should start on your active course, the one you last set up or switched to (it asks which course if there are several and none is active). As a last resort in any app: "Read AGENTS.md in `<course folder path>` before answering".

Course material is the university's: keep it in your own folders and never share it. The repo contains code only.

## Development

- Design: [`docs/spec/v1.md`](docs/spec/v1.md), vocabulary: [`CONTEXT.md`](CONTEXT.md), decisions: [`docs/adr/`](docs/adr/). Ticket history and dated project reviews are kept locally only (gitignored), not in this repo.
- One source of truth: the command line (`plugins/unistudent/scripts/unistudent/cli.py`, `commands.py`). The MCP server generates its tools from it.
- Tests: `python3 -m unittest discover -s tests` (standard library only; CI runs macOS, Windows and Linux on Python 3.9 and 3.12, with and without optional libraries).
- Grounding eval with a real model: `python3 evals/grounding/run.py` (needs the `claude` CLI).
