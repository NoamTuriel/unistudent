---
name: wiki
description: Build or refresh the course Wiki from Raw (conversions, then glossary, question bank, unit pages, course page).
disable-model-invocation: true
---

The Wiki is the course's knowledge base for AI: everything an answer may rely on. Every page cites its sources; nothing enters it from outside the course material.

`us` means `python3 <this skill's base directory>/../../scripts/us.py`.

## 1. Convert

Run `us courses current` (say which course), then `us wiki build --json`.

Done when: the build ran and you have its `units_touched`, `images` and `needs_visual`.

## 2. Read what has no text

For each file in `images` and `needs_visual`, dispatch the `source-reader` subagent (in parallel). It writes the content as Markdown source pages.

## 3. Write the understanding layer

For each unit in `units_touched` (all units on a first build), dispatch one `wiki-unit-writer` subagent, in parallel. Give it the course folder, the unit, and the student's language. Each returns glossary entries and question-bank entries for its unit, and edits only its own unit page.

Then merge what they returned into `wiki/glossary.md` and `wiki/question-bank.md` (formats are in the comments at the top of each file). One entry per term: when two units define a term, keep one entry citing both. Remove the `<!-- unistudent:stub -->` line once a file has entries.

Done when: every touched unit page has its methods, notation and assumptions sections, and every term and question the writers returned is merged.

## 4. The course page

Fill `wiki/course.md` from the exam-information files, formula sheets and past exams: exam format, aids allowed, what the lecturer stresses. Each line cites its source. Unknown → write "not in the course material yet".

## 5. Check

Run `us wiki check`. Fix every problem (broken link, broken anchor, page without sources) and run it again.

Done when: `us wiki check` reports 0 problems.

## 6. Report

Two lines: what changed in the Wiki, and anything the student should add (e.g. "no exam-format file found: add one to inbox/").
