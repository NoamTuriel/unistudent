---
name: openu-sync
description: "University plugin: download new material from an Open University (האוניברסיטה הפתוחה) course site into the course folder. Use for /openu:openu-sync and during UniStudent setup."
---

Download what's new on the student's OpenU course site and hand it to the UniStudent core. The core stores, sorts and adds it to the Wiki; this skill only reaches the site.

`us <command>` is the UniStudent core's tool for that command: the MCP tool named by its words joined with `_` (`us site-status` → `site_status`) when the unistudent MCP server is connected, otherwise `unistudent <command>` in a shell. **Ask**: use your question tool if you have one, otherwise ask in the chat.

How the site works (lists, download method, recordings, ready-made snippets) is in `<this skill's base directory>/references/site.md`. Read it first.

## 1. Course and what's already here

Run `us courses current` (say which course) and `us site-status --json` (URLs already downloaded, with the site date each had). You need access to the student's Downloads folder: that's where the browser saves files.

Done when: you know the course folder, the Downloads folder path, and what's already downloaded.

## 2. Find the course on the site

Use a browser tool that drives the student's own logged-in Chrome (Claude in Chrome, or a browser MCP server attached to their Chrome profile). The site can't be reached without their session. If they aren't logged in, ask them to log in in Chrome themselves: never ask for or type their password. Open `https://opal.openu.ac.il/my/` and pick the course link matching the course (and the current semester). Note its `id`.

Done when: you have the course id.

## 3. List the files

Run the listing snippet from `site.md` for the course id. Add folder contents (open each folder, list its file links). Build one listing item per file: `url`, `name`, `section` (the site's section title, as shown), `kind: "document"`, and `unit_hint: "general"` for past exams, exam information and file stores. Drop URLs already in `site-status`.

Done when: every row of the resources list and every file in every folder is an item or already downloaded.

## 4. Recordings: ask first

Open the course's video collections (links on the course page and in the "וידאו" section). Count the recordings and add up their durations when shown (otherwise about 1.5–3 hours per session). Tell the student: how many, total hours, about 3 GB per three hours at full quality, much less as audio only (enough for transcripts). Ask: all, only unit N, or not now; and full video or audio only. Record the answer with `us context --recording-level <0 skip|1 download|3 transcript and summary>`, and reuse it on later syncs unless the student asks.

For each chosen recording, collect its stream URL with the stream snippet from `site.md` and put it in the listing as `kind: "recording"`, `stream_url`, `name` (title + date), `section`. The URLs expire within hours: download them in this same run.

Done when: the student chose, and every chosen recording has a listing item with a stream URL.

## 5. Download

In the course tab, download every document item with the in-page method from `site.md`, named `unistudent-<course number>-<date>__<name>`, and set each item's `file` to that name. Then download the listing itself as `unistudent-<course number>-<date>__listing.json`.

Then run `us recordings fetch "<Downloads>/<listing file>" "<Downloads>" [--audio-only]` for the recordings.

Done when: every chosen item has a `file`, or is reported as failed.

## 6. Hand over

Run `us ingest --json "<Downloads>/<listing file>" "<Downloads>"`. The core moves the listed files into Raw, sorts them, updates the Wiki, and reports `new`, `changed`, `missing` and `unsorted`.

- `unsorted`: ask one grouped question and record answers with `us assign`.
- `missing`: retry those downloads once, then report them.

Done when: the ingest ran and unsorted files are answered or deferred.

## 7. Report

Two lines: what's new since the last sync, and what's waiting (recordings not downloaded, unsorted files). If a unit with a study pack got new material, offer `/unistudent:study-pack N`. If recordings came in, offer `/unistudent:course-recordings`.
