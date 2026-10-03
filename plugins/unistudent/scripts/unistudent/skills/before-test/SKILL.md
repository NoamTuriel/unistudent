---
name: before-test
description: Build the Before-the-test page: every question of every past exam, grouped by solving method, with question and solution links.
disable-model-invocation: true
---

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. Course and exams

Run `us courses current` and say which course. List the past exams in the Material folder: files whose Wiki source page or name shows an exam with questions (a formula sheet, an assumptions sheet or a syllabus is not one; a Word copy of a PDF is the same exam). If the student's file names leave doubt, show the list and ask.

No past exam: say so in one line and stop.

Done when: you have the exam PDF list (count, and which have a solution), or have stopped.

## 2. Ask first

It is a big job: about 40K subagent tokens per exam (15 exams cost about 600K). Ask once, in plain words: the exam count, the cost, what the page is, and the format (the course format setting, or HTML for the browser). If a page already exists, say it stays untouched and ask whether to make a new one. Go on only on a yes.

Done when: the student said yes, with the format.

## 3. Rules

Read `<this skill's base directory>/../../reference/before-test.md` (or `us doc before-test`), then general preferences and `course-preferences.md`.

## 4. Index

**Delegate** the exams to `exam-indexer` workers, one per two exams, in parallel. Output files `<hidden>/before-test/part-<k>.json` (`<hidden>` is `.unistudent` in the course folder). Re-run any worker whose file is missing or invalid. Then run `us before-test merge <the part files>`.

Done when: `us before-test merge` reports the question count and it matches the exams' questions.

## 5. Cluster

**Delegate** the merged index (`index.json` in that folder) to one `exam-clusterer` worker, output `clusters.json` beside it.

Done when: the worker returned its cluster count.

## 6. Build

Run `us before-test build --format <html|obsidian|markdown>`, adding `--note "<line>"` for anything you could not verify (a step that failed, exams skipped). Open one rendered question copy and one solution page from the first exam to see the links land right.

## 7. Check

Run `us check "<page>"` until it reports 0 problems. Tell the student where the page is, what the notes box says, and that adding an exam later means rebuilding it.

Done when: the check reports 0 problems.
