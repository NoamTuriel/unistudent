---
name: course-recordings
description: Transcribe and summarise course recordings into the Wiki (heavy and slow; always asks first).
disable-model-invocation: true
---

Heavy work starts only after the student says yes to real numbers.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); as the Claude plugin, give them to the plugin's subagent of that name, which has the UniStudent tools (in parallel when there are several); in any other app, follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. What and how much

Run `us courses current`, then `us recordings estimate --json` (add `--unit N` if the student named a unit; suggest the unit they're studying now).

Done when: you have the numbers for the chosen recordings, and the speech-to-text engine is installed.

If `realtime_factor` is empty and a recording exists, offer a one-minute benchmark (`us recordings benchmark "<path>"`) to get a real time estimate. If `backend_installed` is false, show `install_command` (and ffmpeg's install if `ffmpeg` is missing) and stop until installed.

## 2. Ask

Show the totals: number of recordings, hours of audio, GB, estimated time on this machine, and that Claude will also read each transcript (tokens). Then show **one numbered list** of the recordings still without a transcript (`files` from the estimate), each as `N. <full path> - X min, estimated Y on this machine`. Ask which to transcribe: the student answers with numbers ("1, 4, 7") or "none". "All" is not an answer: ask for numbers. Record "none" with `us context --recording-level 0` and a choice with `us context --recording-level 3`.

Then ask a **separate** question about frame analysis (looking at what's on screen, e.g. slides), only if a video-analysis tool is installed: show `frame_analysis_segments` from the same estimate (one extra AI call per segment — real cost, distinct from transcription) and ask yes/no. Default to no unless the student asks for it. Record with `us context --frame-analysis <0 off|1 on>`. Skip this question (and never turn it on) if no video-analysis tool is installed, or if it was already answered for this course.

Done when: the student named recordings by number, or said none; and, if relevant, frame analysis is explicitly on or off.

## 3. Transcribe

Run `us recordings approve "<path>" ...` with exactly the recordings the student numbered: `transcribe` refuses any recording not approved. Tell the student "Sit back and relax, this might take a while.", then run `us recordings transcribe "<path>" ... --background`: it returns at once and writes progress to a log. Tell the student they can keep working, and check with `us recordings list` until every chosen recording has a transcript.

Done when: every chosen recording has a `transcript.md`.

## 4. Table of contents and summary

For each transcript, **delegate** to one `recording-summarizer` worker, telling it explicitly whether frame analysis is on for this course (`.unistudent/settings.json`'s `frame_analysis`: on only if `true`, off for `false` or unset — never let the worker decide from tool availability alone). Each writes `toc.md` and `summary.md` next to the transcript (in the hidden Wiki) and returns a three-line summary. Only those three lines come back to you.

Done when: every transcript has `toc.md` and `summary.md`.

## 5. Where each recording belongs

A recording of a whole class session often teaches several units at once, so it belongs to no unit: it goes to **Recorded lessons**. Decide from the recording's meaning, never from a keyword list: read each recording's whole file name and its folder names (in any language or naming scheme the university uses) and judge whether it is a whole class session, a recording that solves one question, or something else. A name that settles it is enough. If it does not, read the start of the transcript. If you are still unsure, ask the student one grouped question. Record each class session with `us assign "<path>" lessons`; a recording that solves a question stays in its unit.

Done when: every class session is assigned to `lessons` or the student deferred it.

## 6. Update

Run `us wiki build` (the unit pages now link the summaries, and each unit's recordings roadmap, and the Recorded lessons roadmap, with the announcements and exam hints, is written into the student's Study vault), then **delegate** each unit in its `units_touched` to one `wiki-unit-writer` worker (a new table of contents lets it fill "Solved in a recording"; update the matching entries of `question-bank.md` in the Wiki, the `wiki` folder in `us courses current`, with the entries it returns), then `us wiki check`.

Done when: every unit in `units_touched` was rewritten and `us wiki check` reports 0 problems. If a new recorded lesson covers a unit that has a study pack (read the lesson's first summary line for the units), offer `/unistudent:study-pack N` to rebuild that unit's Recordings index page; `us study changes` cannot see lessons, since they belong to no unit.

Report: which recordings are done (and that each unit's roadmap, and the Recorded lessons roadmap, is in the study vault), and the announcements and "this will be on the exam" moments the summarizers found.
