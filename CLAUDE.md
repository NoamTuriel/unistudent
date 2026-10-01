# UniStudent

## What this is and who it's for

UniStudent turns one university student's course material (PDFs, slides, recordings, whatever the
course gives them) into a per-course, AI-readable Wiki, so an AI answers the student's questions from
*their* course only, and helps them study it. It's real software for a real, single user (Noam, an Open
University of Israel student) building his first AI plugin — not a hypothetical product.

What actually matters to that user, in his own words — every design or code decision should be judged
against these, not just against "does it pass tests":

1. **Trust.** A general AI answers from the whole internet (other notation, other methods, other
   courses); this one must answer only from the student's own course material, and say so on every
   paragraph: ✅ from the material, 💡 the AI's own explanation of it, ⚠️ outside it, ❌ conflicts with it.
2. **Feeding it new material must be easy, and the student must know how.** Dropping a file in and
   getting it into the Wiki is not enough if the student doesn't know that's the move — `course-add` and
   the inbox exist for this, and every setup/help flow must actually tell the student about them, not
   assume they'll find `README.md`.
3. **Works for every course and every university, not just OpenU and economics out of the box.**
   `openu` and `economics` are the first, most-polished plugins, not the ceiling — a student anywhere
   else must still get a working (if less tailored) experience: a generated, once-interviewed fallback
   (ADR 0005) instead of a dead end. Treat "no plugin for this" as a case to design for, always, not an
   edge case to skip.
4. **Teachers' spoken announcements must survive.** A lecturer saying "tomorrow I want you to tell me who
   you're working with next week" mid-recording is exactly the kind of thing a student needs written
   down, highlighted, and linked to the exact time and recording it was said in — not summarized away.
   This is a first-class output of recording processing, not a nice-to-have (see
   `agents/recording-summarizer.md`'s `## Announcements` and `## "This will be on the exam"` sections).
5. **Unit summaries (study packs) should work out of the box.** A student with no course-specific skill
   installed still gets a real, usable summary from the generic rules — good defaults matter as much as
   the ability to customize per course.
6. **Setup must be easy for non-technical users.** Plain language, no unexplained jargon, one question at
   a time, a real explanation of what just happened and what to do next — not a checklist for someone who
   already knows what an MCP server is.
7. **Must work on every OS and every AI harness**, not just the one being developed on: Windows, macOS
   and Linux; Claude Code, Claude Desktop, Cowork, Cursor, VS Code, Codex, Gemini CLI, or any other app
   that speaks MCP or Agent Skills. CI runs the test matrix across OSes and Python versions for exactly
   this reason.

Three Claude plugins from one Python codebase: `unistudent` (core: course folders, the Wiki, recordings,
study packs, grounding — works for any university via point 3 above), `openu` (Open University of Israel:
downloads new material from the course site), `economics` (study-pack rules for economics courses). The
MCP server and skills are auto-generated from the same command line, so the same code also works in any
MCP client — not just Claude — per point 7.

**Start here, in this order:** `README.md` (what it is, how to install, the folder layout) →
`CONTEXT.md` (vocabulary — use these exact words in code, tests, skills and docs, nowhere else) →
`docs/spec/v1.md` then `docs/spec/v2.md` (design, in order shipped) → `docs/adr/` (why specific decisions
were made) → the newest `docs/review-*.md` (an honest, dated audit of what's actually solid vs. still
weak — read the most recent one, not this file, for current known gaps) → `.scratch/unistudent-*/issues/`
(ticket history; anything `ready-for-agent` there is open work, not yet done).

## Privacy: nothing personal ever reaches the remote

This repo is public. Before any push or commit, check for and never include: personal email addresses,
IP addresses, phone numbers, real names beyond the author's own public GitHub attribution, session or
chat URLs, or specific personal identifying details (e.g. a too-specific real course name/number tied to
one person) in commit messages, code, docs, or tickets. `.scratch/` (ticket history) and
`docs/review-*.md` (dated project reviews) are gitignored on purpose — they're working notes for local
use only, not meant to be public. If in doubt about whether something is personal, leave it out and ask.

## Working on this repo

- Use the vocabulary in `CONTEXT.md` in code, tests, skills and docs. Respect the decisions in `docs/adr/`.
- Tests: `python3 -m unittest discover -s tests`. Write tests only at the three seams (sync, Wiki build, grounding), through the `us.py` command line.
- Scripts: Python standard library only; optional libraries behind `try/except ImportError`. OS-specific behaviour lives in `recordings.py` only.
- The CLI (`cli.py`, `commands.py`) is the single source of truth: the MCP server generates its tools from the argument parser, so a new command or option is automatically a tool.
- Core skills share one conventions block (`us` / delegate / ask); `tests/test_skills.py` keeps it identical. Use existing tools before writing new ones (markitdown, ffmpeg, faster-whisper / mlx-whisper, mcp-video-analyzer).
- Skills and agents follow `writing-for-agents`: steps with "Done when" criteria, one source of truth per rule. The grounding rule's single source is `plugins/unistudent/scripts/unistudent/templates/context.md`; study-pack generic rules live in `plugins/unistudent/scripts/unistudent/reference/study-pack.md`.
- Subject plugins never depend on a university plugin; university plugins never hold study-pack rules.
- Never commit course material.
