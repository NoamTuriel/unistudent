---
name: help
description: Explain how UniStudent works and what it can do next.
disable-model-invocation: true
---

`us` means `python3 <this skill's base directory>/../../scripts/us.py`.

1. Run `us courses current --json`. No course → say so and offer `/unistudent:setup`. Otherwise start with "Working on: <name>".
2. Explain from the course folder's `README.md`, in the student's language and in the student's words: the flow (course material → Wiki → study packs), the inbox, and the grounding labels. Keep it to what fits one screen.
3. Show what is waiting, from real state:
   - `us unsorted --json`: files that need a unit.
   - `us recordings list --json`: recordings not processed.
   - `ls inbox/`: files not added yet.
   - Units without a study pack: `wiki/units/` compared with `study/`.
4. Offer the commands that apply now, one line each:

| Command | When |
|---|---|
| `/unistudent:add` | files are in `inbox/` |
| `/unistudent:wiki` | the Wiki is missing or stale |
| `/unistudent:unit` | a unit has no study pack, or new material arrived for one |
| `/unistudent:recordings` | recordings aren't processed |
| `/unistudent:courses` | switch course |
| `/unistudent:setup` | add another course |
| `/openu:sync` (or the student's university plugin) | new material on the course site |

Done when: the student has seen what's waiting and the commands that apply.
