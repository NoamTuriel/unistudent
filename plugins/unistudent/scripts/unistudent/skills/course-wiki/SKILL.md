---
name: course-wiki
description: Build or refresh the course Wiki from Raw (conversions, then glossary, question bank, unit pages, course page).
disable-model-invocation: true
---

The Wiki is everything an answer about the course may rely on. Every page cites its sources; nothing enters it from outside the course material.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. Convert

Run `us courses current` (say which course), then `us wiki build --json`.

Done when: the build ran and you have its `units_touched`, `images` and `needs_visual`.

## 2. Read what has no text

For each file in `images` and `needs_visual`, **delegate** to the `source-reader` worker (one per file). It writes the content as Markdown source pages.

Done when: every listed file has a source page.

## 3. Write the understanding layer

For each unit in `units_touched` (all units on a first build), **delegate** to one `wiki-unit-writer` worker. Give it the course folder, the unit, and the student's language. Each returns glossary entries and question-bank entries for its unit, and edits only its own unit page.

Then merge what they returned into `wiki/glossary.md` and `wiki/question-bank.md` (formats are in the comments at the top of each file). One entry per term: when two units define a term, keep one entry citing both. Remove the `<!-- unistudent:stub -->` line once a file has entries.

Done when: every touched unit page has its methods, notation and assumptions sections, and every term and question the writers returned is merged.

## 4. The course page

Fill `wiki/course.md` from the exam-information files, formula sheets and past exams: exam format, aids allowed, what the lecturer stresses. Each line cites its source. Unknown → write "not in the course material yet".

Done when: each section of `wiki/course.md` has content with sources, or says it's not in the material yet.

## 5. Check

Run `us wiki check`. Fix every problem (broken link, broken anchor, page without sources) and run it again.

Done when: `us wiki check` reports 0 problems.

## 6. Report

Two lines: what changed in the Wiki, and anything the student should add (e.g. "no exam-format file found: add one to inbox/").
