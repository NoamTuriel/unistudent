---
name: recordings
description: Transcribe and summarise course recordings into the Wiki (heavy and slow; always asks first).
disable-model-invocation: true
---

Recordings are the most valuable and the most expensive material: hours of audio per session. Nothing heavy starts without the student's yes after seeing real numbers.

`us` means `python3 <this skill's base directory>/../../scripts/us.py`.

## 1. What and how much

Run `us courses current`, then `us recordings estimate --json` (add `--unit N` if the student named a unit; suggest the unit they're studying now).

If `realtime_factor` is empty and a recording exists, offer a one-minute benchmark (`us recordings benchmark "<path>"`) to get a real time estimate. If `backend_installed` is false, show `install_command` (and ffmpeg's install if `ffmpeg` is missing) and stop until installed.

## 2. Ask

Show: number of recordings, hours of audio, GB, estimated time on this machine, and that Claude will also read each transcript (tokens). Ask: all of them, only unit N, or not now. Record the answer with `us context --video-level <0 skip|1 download only|3 transcript and summary>`.

Done when: the student said yes to a specific list, or no.

## 3. Transcribe

Run `us recordings transcribe "<path>"` for each chosen recording, one at a time, in the background where possible. Tell the student they can keep working.

## 4. Table of contents and summary

For each transcript, dispatch one `recording-summarizer` subagent (in parallel). Each writes `toc.md` and `summary.md` next to the transcript and returns a three-line summary. Only those three lines come back to you.

## 5. Update

Run `us wiki build` (the unit pages now link the summaries) and `us wiki check` until it reports 0 problems. If a unit with a study pack got new recordings, offer `/unistudent:unit N` for proposed changes.

Report: which recordings are done, and the announcements and "this will be on the exam" moments the summarizers found.
