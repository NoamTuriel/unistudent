---
name: course-wiki
description: Build or refresh the course Wiki from the Material folder (conversions, then glossary, question bank, unit pages, course page).
disable-model-invocation: true
---

The Wiki is everything an answer about the course may rely on. Every page cites its sources; nothing enters it from outside the course material. The Wiki lives in the hidden folder: its path is `wiki` in `us courses current`, and `<wiki>` below means that folder.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); as the Claude plugin, give them to the plugin's subagent of that name, which has the UniStudent tools (in parallel when there are several); in any other app, follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. Convert

Run `us courses current` (say which course), then `us wiki build --json`. The build first reads the Material folder as the student left it: files they moved or renamed are followed, files they deleted leave the Wiki, and new files they put there are added.

Done when: the build ran and you have its `units_touched`, `images` and `needs_visual`.

## 2. Read what has no text

For each item in `images` and `needs_visual`, **delegate** to the `source-reader` worker (one per item, given the whole item, the course folder and the course language). It writes the content as Markdown source pages. Then run `us wiki build` again, so `coverage.md` counts them as analyzed.

Done when: every listed item has a source page and the second build lists no `images` or `needs_visual`.

## 3. Write the understanding layer

For each unit in the `units_touched` of step 1's build, plus any the second build in step 2 adds (all units on a first build), **delegate** to one `wiki-unit-writer` worker. Give it the course folder, the unit, and the student's language. Each edits only its own unit page and merges its glossary and question-bank entries itself with `us wiki merge` (one writer at a time, so writers in parallel lose nothing): never edit `<wiki>/glossary.md` or `<wiki>/question-bank.md` yourself.

Done when: every touched unit page has its methods, notation and assumptions sections, and every writer reported its merge counts.

## 4. The course page

Fill `<wiki>/course.md` from the exam-information files, formula sheets and past exams: exam format, aids allowed, what the course stresses. Each line cites its source. Unknown → write "not in the course material yet". Nothing at all to cite yet (a self-study course, or no exam files so far) → leave the page as it is: its stub line marks it as not filled, and `us wiki check` accepts it.

Done when: each section of `<wiki>/course.md` has content with sources or says it's not in the material yet, or the page is left as its stub because nothing can be cited.

## 5. Check

Run `us wiki check`. Fix every problem (broken link, broken anchor, page without sources) and run it again.

Done when: `us wiki check` reports 0 problems.

## 6. Report

Two lines: what changed in the Wiki, and anything the student should add (e.g., for a course with an exam, "no exam-format file found: drop one in the inbox").
