---
name: openu-sync
description: "University plugin: download new material from an Open University (האוניברסיטה הפתוחה) course site into the course folder. Use for /openu:openu-sync and during UniStudent setup."
---

Download what's new on the student's OpenU course site and hand it to the UniStudent core. The core stores, sorts and adds it to the Wiki; this skill only reaches the site.

`us <command>` is the UniStudent core's tool for that command: the MCP tool named by its words joined with `_` (`us site-status` → `site_status`) when the unistudent MCP server is connected, otherwise `unistudent <command>` in a shell. **Ask**: use your question tool if you have one, otherwise ask in the chat.

How the site works (lists, sizes, download method, recordings, ready-made snippets) is in `<this skill's base directory>/references/site.md`. Read it first.

The sync runs in three parts: scan the site without downloading (steps 1-3), show the Fetch plan and wait for the student's OK (step 4), then download without asking anything (steps 5-6). **Inside setup**, course setup tells you so when it starts this skill: it runs steps 1-4 before the student leaves and steps 5-6 in its unattended run, and does its own report (step 7 is skipped).

There are two ways in. **With a Saved login** (the student's OpenU username, password and ID number, kept on their computer), `us openu` logs in, scans and downloads by itself, with no browser. **Through Chrome**, every scan and download is a script run in the student's logged-in Chrome tab. Use the Saved login when there is one; Chrome otherwise, or when the Saved login stops working. Never ask for the password in the chat, never type it anywhere, and never open `logins.json`: `us openu login` opens a form on the student's computer, and only that form takes the password.

## 1. Course and what's already here

Run `us courses current` (say which course), `us openu status` (whether there is a Saved login) and `us site-status --json` (URLs already downloaded, and `last_sync`, the date of the last sync). Read the course's Recording choice from `.unistudent/settings.json` in the course folder: `recording_level` (0 skip, 1 download only, 3 transcript and summary). You need access to the student's Downloads folder: that's where the browser saves files.

Ask the recordings question only when `recording_level` is `null` (an older course synced outside setup): transcribe and summarise them (recommended: the AI can then answer from what the lecturer said and link to the minute), download them only, or skip them. Record it with `us context --recording-level <3|1|0>`; it holds for every later sync.

Done when: you know the course folder, the Downloads folder path, what's already downloaded, `last_sync`, and the Recording choice.

## 2. Find the course on the site

**With a Saved login:** run `us openu scan` with no `--course-id`: it lists the student's courses (`id`, name and semester). Pick the one matching the course and the current semester. If it says the site didn't accept the Saved login, say so in one line and ask: type it again (`us openu login`, which opens the form; tell the student before you run it) or go through Chrome this time. Never retry the same login.

**Through Chrome** (no Saved login): use a browser tool that drives the student's own logged-in Chrome (Claude in Chrome, or a browser MCP server attached to their Chrome profile). The site can't be reached without their session. No such tool → offer the Saved login: "Should I save your OpenU login on this computer? A form opens in your browser and the AI never sees it. Then I can download new material without you logging in." Yes → `us openu login`, then follow the Saved login way. No → stop here and say so in plain words: it is not an error and nothing is lost; they can add Claude in Chrome (a free Chrome extension; in Claude Code, connect it with `/chrome`) and run the sync again, or download the files themselves, drop them in the course's inbox and run `course-add`. If they aren't logged in, ask them to log in in Chrome themselves: never ask for or type their password. Open `https://opal.openu.ac.il/my/` and pick the course link matching the course (and the current semester). Note its `id` and the course number.

Done when: you have the course id and number.

## 3. Scan, without downloading

Nothing downloads in this step, and no stream links are collected: they expire within hours.

**With a Saved login:** run `us openu scan --course-id <id> "<Downloads>"`. It does everything below (files, folders, video collections, recordings with their lengths, their attached files, sizes and types; recordings left out when `recording_level` is 0) and writes the listing into Downloads; its `listing` is the path. Then go to step 4.

**Through Chrome:**

- **Documents:** run the listing snippet from `site.md` for the course id, then add folder contents (open each folder, list its file links). One item per file: `url`, `name`, `section` (the site's section title, as shown), `kind: "document"`, and `unit_hint: "general"` for past exams, exam information and file stores. Then run the size and type snippet: it adds `size`, and `file` (`unistudent-<course number>-<date>__<name>.<real file type>`, the name it will be downloaded under), without downloading anything. Its last count must be 0: a `file` without its type can't be read into the Wiki.
- **Assignments:** with a Saved login `us openu scan` lists them already (the course's `ouilassign` module, not the resources list). Through Chrome, run the assignments snippet from `site.md` in each course tab. Each is an item with `kind: "assignment"`, `due`, `status` and `download` (its file); it is listed on every sync, also when already downloaded: `us fetch-plan show` updates the dates and statuses of the ones already in, even when nothing else is new. Never list the student's own submitted files.
- **Recordings and their attached files:** run the recordings snippet in each video collection (links on the course page and in the "וידאו" section), even when `recording_level` is 0: lecturers hang files on recordings (the class exercise file, the exam-prep file) that are in no other list. Every file in a recording's `attachments` is a document item, with `attached_to`: that recording's `url` (collection URL + `#` + title, also when no recording item is added), so the recording's summarizer reads it. When `recording_level` is 0, add no recording items (count them for the report); otherwise one item per recording: `url` (the collection URL + `#` + the title), `title` (exactly as shown), `name` (title + date), `section`, `kind: "recording"`, and `seconds` as the snippet read it from the player (the length is what makes the Fetch plan's time real: recordings of unknown length leave the student no time to plan around).

Download the listing `{"course_site": ..., "items": [...]}` from the course tab with the in-page method, as `unistudent-<course number>-<date>__listing.json` (list everything: the Fetch plan leaves out what is already downloaded).

Done when: every row of the resources list, every file in every folder, every file attached to a recording and every recording the Settings want is an item or already downloaded, and the listing file is in Downloads.

## 4. The Fetch plan

On every sync, inside setup or not, run `us fetch-plan show --json "<Downloads>/<listing file>"`. When its `nothing_new` is true, say its `summary` ("Nothing new on the site since <date>") in one line and stop: no empty plan. Otherwise show its `summary` (totals per file type, free disk space, rough time) and the checklist path, then ask: **download all**, **skip all recordings**, or **edit the list** (untick lines in the checklist file, or say it in the chat: "skip unit 1 recordings", "drop the old exams").

- Skip all recordings: untick every recording line (`.mp4`, or `.m4a` when only the sound is kept) in the checklist.
- Edit the list: make each change the student asks for in the checklist (change `[x]` to `[ ]`), run `us fetch-plan show` again and show the new `summary`. Repeat until the student says OK.
- When `fits` is false, say so and ask what to untick before going on.

**Inside setup**, ask one grouped question about the `needs_unit` files: a unit number, general, or "I don't know" (the file stays unsorted but is still read into the Wiki).

Only after an explicit OK (download all, skip all recordings, or OK to the edited list) run `us fetch-plan apply --json "<Downloads>/<listing file>" [--unit NUMBER=UNIT ...]` (`unknown` for "I don't know"). Its `listing` is the approved listing: download from it, nothing else.

Done when: the student gave an explicit OK and `fetch-plan apply` returned the approved listing.

## 5. Download the documents and hand them over

From here to the end, never ask: a failure is retried once, then skipped and reported.

With a Saved login, run `us openu download "<approved listing>" "<Downloads>"` (it skips what is already in and retries a failure once). Through Chrome, in the course tab, download every document item of the approved listing whose `url` is not in `us site-status` yet (a resumed run skips what is already in), with the in-page method from `site.md`, under its `file` name. Then run `us ingest --json "<approved listing>" "<Downloads>"`. The core moves the files into the course's Material folder (`official`, by unit), updates the Wiki, and reports `new`, `changed`, `missing` and `unsorted`. Download each `missing` file once more and run the ingest again; what is still missing goes in the report.

Done when: every approved document is ingested or listed as failed.

## 6. Download the recordings, one at a time

For each recording item of the approved listing whose `url` is not in `us site-status` yet (a resumed run skips what is already in), oldest first (by the recording date), and only now:

With a Saved login, run `us openu stream "<approved listing>" "<Downloads>" --url "<the item's url>"`: it collects the link, downloads the recording (collecting the link again once if that fails) and returns `listing`, the one-recording listing. Then run `us ingest --json --no-wiki "<that listing>" "<Downloads>"`. A recording it couldn't download goes in the report. Through Chrome:

1. In its collection tab, run the stream snippet from `site.md` with the item copied exactly from the approved listing (rebuilding it from the page loses its `transcribe` tick): it collects that one recording's link and downloads a one-recording listing, `unistudent-<course number>-<date>__rec-<n>.json`.
2. Run `us recordings fetch --json "<Downloads>/<that file>" "<Downloads>"` (it keeps the sound only when the Settings say so).
3. If it failed (an expired link, usually), collect its link again once (`__rec-<n>-again.json`) and fetch again; if that fails too, skip the recording and add it to the report.
4. Run `us ingest --json --no-wiki "<Downloads>/<that file>" "<Downloads>"`. A recording ticked for transcripts is approved for transcription as it lands.

After the last recording, run `us wiki build` once.

Done when: every approved recording is ingested or listed as failed, and the Wiki was built once after them.

## 7. Report

Inside setup, skip this step: hand setup what's new, what failed, the `unsorted` files and the units in `wiki.units_touched`.

Outside setup:

- `unsorted` files: ask one grouped question: a unit number, general, or "I don't know". Record answers with `us assign`; "I don't know" leaves the file unsorted, already in the Wiki.
- Give each unit in `wiki.units_touched` (all ingests together) to the unistudent `wiki-unit-writer` worker (`us doc wiki-unit-writer` gives its instructions); it merges its own glossary and question-bank entries.
- Open assignments: run `us assignments --json`. Any open → one line (how many, the soonest due date) and offer `/unistudent:course-assignments`: it scans the files for text aimed at an AI first, checks the Wiki can solve them, and only then offers to solve. Offer it; never start it unasked, and nothing is ever submitted for the student.
- Two lines: what's new since the last sync, and what's waiting (failed downloads with what to do, recordings the Settings skip, unsorted files). If a unit with a study pack got new material, offer `/unistudent:study-pack N`. If recordings came in, offer `/unistudent:course-recordings`.

Done when: unsorted files are answered or left unsorted by choice, every touched unit went to the unit writer, open assignments were offered, and the two lines were said.
