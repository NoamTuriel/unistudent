---
name: course-recordings
description: Transcribe and summarise course recordings into the Wiki (heavy and slow; always asks first).
disable-model-invocation: true
---

Heavy work starts only after the student says yes to real numbers.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. What and how much

Run `us courses current`, then `us recordings estimate --json` (add `--unit N` if the student named a unit; suggest the unit they're studying now).

Done when: you have the numbers for the chosen recordings, and the speech-to-text engine is installed.

If `realtime_factor` is empty and a recording exists, offer a one-minute benchmark (`us recordings benchmark "<path>"`) to get a real time estimate. If `backend_installed` is false, show `install_command` (and ffmpeg's install if `ffmpeg` is missing) and stop until installed.

## 2. Ask

Show: number of recordings, hours of audio, GB, estimated time on this machine, and that Claude will also read each transcript (tokens). Ask: all of them, only unit N, or not now. Record the answer with `us context --recording-level <0 skip|1 download only|3 transcript and summary>`.

Then ask a **separate** question about frame analysis (looking at what's on screen, e.g. slides), only if a video-analysis tool is installed: show `frame_analysis_segments` from the same estimate (one extra AI call per segment — real cost, distinct from transcription) and ask yes/no. Default to no unless the student asks for it. Record with `us context --frame-analysis <0 off|1 on>`. Skip this question (and never turn it on) if no video-analysis tool is installed, or if it was already answered for this course.

Done when: the student said yes to a specific list of recordings, or no; and, if relevant, frame analysis is explicitly on or off.

## 3. Transcribe

Run `us recordings transcribe "<path>" ... --background`: it returns at once and writes progress to a log. Tell the student they can keep working, and check with `us recordings list` until every chosen recording has a transcript.

Done when: every chosen recording has a `transcript.md`.

## 4. Table of contents and summary

For each transcript, **delegate** to one `recording-summarizer` worker, telling it explicitly whether frame analysis is on for this course (`.unistudent/settings.json`'s `frame_analysis`: on only if `true`, off for `false` or unset — never let the worker decide from tool availability alone). Each writes `toc.md` and `summary.md` next to the transcript and returns a three-line summary. Only those three lines come back to you.

Done when: every transcript has `toc.md` and `summary.md`.

## 5. Update

Run `us wiki build` (the unit pages now link the summaries), then `us wiki check`.

Done when: `us wiki check` reports 0 problems. If a unit with a study pack got new recordings, offer `/unistudent:study-pack N` for proposed changes.

Report: which recordings are done, and the announcements and "this will be on the exam" moments the summarizers found.
