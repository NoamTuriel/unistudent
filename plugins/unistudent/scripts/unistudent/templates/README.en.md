# {course_name}: how this folder works

This folder is your whole course in one place. Claude answers questions about the course **only from the material here**, not from the internet, so answers match your course's methods, notation and assumptions: the things your exam grades.

## What's here

You see three folders, numbered in the order you use them. Everything else is hidden in `.unistudent/` (the Wiki, settings and saved state), so it can't be broken by accident.

| Folder | What it is | Who writes in it |
|---|---|---|
| `{inbox}/` | Drop new files here: a friend's summary, an exam, a photo of notes | you |
| `{material}/` | The real files of the course, sorted by trust level (`official/`, `added/`) and then by unit. Move, rename or delete files here: where a file sits is what counts, and moving one between `official/` and `added/` changes how far it is trusted. **Deleting here deletes the only copy** (your computer's Trash can bring it back) | you and the plugin |
| `{study}/` | **Open this folder as your vault** (in Obsidian or any other app). Only what was made for you to study from: study packs and a recordings roadmap per unit | the plugin proposes; the packs are yours |

## Feeding Claude more material

1. Drop a file into `{inbox}/`.
2. Run `/unistudent:course-add`.
3. Claude moves it into `{material}/added/`, sorts it into a unit, updates the Wiki, and uses it in answers from then on. The inbox ends up empty: an empty inbox means everything was handled.

You can also put files straight into `{material}/`: the next Wiki build notices them, and notices moves, renames and deletions too. The more course material there is, the more precise the answers.

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
| `/unistudent:course-add` | Processes what's in `{inbox}/` |
| `/unistudent:course-wiki` | Builds or refreshes the Wiki |
| `/unistudent:study-pack` | Builds a study pack for a unit (you pick the pages) |
| `/unistudent:course-recordings` | Transcribes and summarises recordings (heavy and slow; always asks first) |
| `/unistudent:courses` | Lists your courses and switches between them |

## Preferences

When you ask for a change that affects a whole unit (e.g. "shorter explanations"), Claude asks: only this unit, always for this course, or for all my courses. The answer is saved in `course-preferences.md` or in your general preferences.
