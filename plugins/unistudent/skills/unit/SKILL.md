---
name: unit
description: Build a study pack for one unit (the student picks the pages), or propose updates to an existing one.
disable-model-invocation: true
---

`us` means `python3 <this skill's base directory>/../../scripts/us.py`. The generic rules are in `<this skill's base directory>/../../reference/study-pack.md`.

## 1. Course and unit

Run `us courses current` and say which course. Get the unit number from the student's request, or ask.

## 2. Existing pack → propose, never overwrite

If `study/<unit label>/` exists, run `us study changes --unit N --json`.

- `has_study_pack` and changes: read the new and changed Wiki pages and draft a change list ("2 new questions for topic 3 from <source>: add them?"). Apply only what the student approves, then run `us study mark-built --unit N`. Stop.
- No changes: say the pack is up to date and ask what they want changed.

Study packs belong to the student: never rewrite a page they didn't approve.

## 3. Resolve the rules

Read, in this order (later wins):

1. the generic rules (reference above);
2. the field and course skills: if `.unistudent/settings.json` names a `course_skill`, invoke it with the Skill tool (it names its field skill; invoke that too);
3. general preferences, then `course-preferences.md` (paths in the course's `CLAUDE.md`).

Done when: you know the page list, each page's content rules, and the concept structure.

## 4. Pick pages

Ask with AskUserQuestion (multiSelect): every available page with its one-line "what it gives you", all default pages selected. Skip the recordings page when the unit has no transcripts, and say why.

## 5. Build

Dispatch one `unit-pack-writer` subagent with: course folder, unit, the chosen pages, the resolved rules (paste them in full: the subagent has no access to your skills), the format (Obsidian or Markdown) and the language.

## 6. Verify

Dispatch the `verifier` subagent on `study/<unit label>/`. Fix what it reports, then run it again.

Done when: `us check --labels "study/<unit label>"` reports 0 problems.

Then run `us study mark-built --unit N`.

## 7. Change requests during the session

A change to one paragraph or explanation: just make it. A change to the whole pack or how material is handled: ask "only this unit, always for this course, or for all my courses?" and save the last two with `us prefs add --scope course|general --text "<the rule>"`. Skills are never edited.
