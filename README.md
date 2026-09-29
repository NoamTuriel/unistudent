# UniStudent

Claude plugins for university students. Your course material becomes a per-course Wiki that Claude answers from, with every answer marked by where it came from, and study packs built for each unit.

**Why:** a general AI answers from the whole internet: methods your course doesn't teach, other notation, material from other courses. Your exam grades your course's way. UniStudent keeps Claude inside your course material and tells you when it steps outside:

- ✅ from your course material, with a link to the exact page or recording time
- 💡 Claude's own explanation of your course material (an example, an analogy, a memory trick), linked to what it explains
- ⚠️ not in your course material
- ❌ conflicts with how your course does it (the course version comes first)

## Plugins

| Plugin | What it does |
|---|---|
| `unistudent` | Core, any university: course folders, the Wiki, recordings, study packs, grounding labels, preferences |
| `openu` | Open University of Israel: downloads new material from your course site |
| `economics` | Economics study-pack rules, and the intro macroeconomics course skill |

## Install

Claude Code:

```
/plugin marketplace add <this repo's GitHub URL or local path>
/plugin install unistudent@unistudent
/plugin install openu@unistudent        # Open University students
/plugin install economics@unistudent    # economics courses
```

Then, for each course: `/unistudent:course-setup`.

You'll need Python 3.9+. Optional, for better results: `pip install -r plugins/unistudent/scripts/requirements.txt`, LibreOffice (Word files with formulas), poppler (`pdftotext`), and for recordings ffmpeg plus `mlx-whisper` (Apple silicon) or `faster-whisper` (everything else).

## Commands

| Command | What it does |
|---|---|
| `/unistudent:course-setup` | Set up a course (run once per course) |
| `/unistudent:course-help` | How it works, and what's waiting |
| `/unistudent:course-add` | Add what you dropped into the course's `inbox/` |
| `/unistudent:course-wiki` | Build or refresh the Wiki |
| `/unistudent:study-pack` | Build a study pack for a unit, or review proposed updates |
| `/unistudent:course-recordings` | Transcribe and summarise recordings (heavy; always asks first) |
| `/unistudent:courses` | List and switch courses |
| `/openu:openu-sync` | Download what's new on your OpenU course site |

## A course folder

```
<course>/
  CLAUDE.md             course context: the grounding rules, exam facts, other courses
  README.md             how it works, for the student
  course-preferences.md
  inbox/                drop new material here
  materials/            everything by unit (links, never copies)
  raw/                  every original file, once
  wiki/                 what Claude reads: sources, units, glossary, question bank, recordings
  study/                your study packs
  .unistudent/          settings and manifest
```

Each course has its own folder and its own Wiki. In Cowork, make one project per course with that folder connected; in Claude Code, start Claude inside the folder.

## Development

- Design: [`docs/spec/v1.md`](docs/spec/v1.md), vocabulary: [`CONTEXT.md`](CONTEXT.md), decisions: [`docs/adr/`](docs/adr/), tickets: [`.scratch/unistudent-v1/issues/`](.scratch/unistudent-v1/issues/).
- Scripts are Python standard library only (optional libraries improve conversion), one codebase for macOS, Windows and Linux.
- Tests: `python3 -m unittest discover -s tests`. They sit at three seams: sync (course site or own folder → Raw), Wiki build (Raw → Wiki), grounding (answers → labels and citations).
- Grounding eval with the real model: `python3 evals/grounding/run.py` (needs the `claude` CLI).
- The repo holds code and skills only. Never commit course material.
