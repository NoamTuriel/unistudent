# {course_name}: how this folder works

This folder is your whole course in one place. Claude answers questions about the course **only from the material here**, not from the internet, so answers match your course's methods, notation and assumptions: the things your exam grades.

## What's here

| Folder | What it is | Who writes in it |
|---|---|---|
| `materials/` | All course files by unit. Links, not copies: every file is stored once | the plugin |
| `raw/` | The source: every file exactly as received | the plugin |
| `wiki/` | The course knowledge in a form Claude reads: text of every file, recording transcripts, glossary, question bank | the plugin |
| `study/` | Your study packs, one per unit | you; the plugin only proposes changes |
| `inbox/` | Drop new material here: a friend's summary, an exam, a photo of notes | you |

## Feeding Claude more material

1. Drop a file into `inbox/`.
2. Run `/unistudent:course-add`.
3. Claude sorts it into a unit, updates the Wiki, and uses it in answers from then on.

The more course material there is, the more precise the answers.

## Labels in answers

- ✅ From course material, with a link to the source.
- 💡 Claude's own explanation (an example, analogy or trick) of something in the course material, linked to what it explains.
- ⚠️ Not in course material. General knowledge; may not match the exam.
- ❌ Conflicts with the course. The course version comes first, then the explanation.

## Commands

In Claude Code type them as shown; in other AI apps, ask for the skill by name (e.g. "run course-add").

| Command | What it does |
|---|---|
| `/unistudent:course-help` | How the plugin works and what it can do |
| `/unistudent:course-add` | Processes what's in `inbox/` |
| `/unistudent:course-wiki` | Builds or refreshes the Wiki |
| `/unistudent:study-pack` | Builds a study pack for a unit (you pick the pages) |
| `/unistudent:course-recordings` | Transcribes and summarises recordings (heavy and slow; always asks first) |
| `/unistudent:courses` | Lists your courses and switches between them |

## Preferences

When you ask for a change that affects a whole unit (e.g. "shorter explanations"), Claude asks: only this unit, always for this course, or for all my courses. The answer is saved in `course-preferences.md` or in your general preferences.
