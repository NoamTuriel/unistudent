---
name: sync
description: "University plugin: download new material from an Open University (האוניברסיטה הפתוחה) course site into the course folder. Use for /openu:sync and during UniStudent setup."
---

Download what's new on the student's OpenU course site and hand it to the UniStudent core. The core stores, sorts and adds it to the Wiki; this skill only reaches the site.

`us` means the UniStudent core's `python3 <core plugin>/scripts/us.py`: find it with Glob for `**/unistudent/scripts/us.py` under the plugins folder that holds this skill.

Site knowledge (URLs, page structure, where recordings live) is in `<this skill's base directory>/../../reference/site.md`. Read it first.

## 1. Course and what's already here

Run `us courses current` (say which course) and `us site-status --json` (URLs already downloaded).

## 2. Open the course site

Use Claude in Chrome with the student's own logged-in session. If they aren't logged in, ask them to log in in Chrome themselves: never ask for or type their password. Open the course page as `site.md` describes.

## 3. Build the listing

Walk every section of the course site and list every file as one item:

```json
{"course_site": "<course page URL>",
 "items": [{"url": "...", "name": "<file name as shown>", "section": "<section title as shown>",
            "file": "<downloaded file name, once downloaded>", "kind": "document|recording",
            "unit_hint": 4}]}
```

- `section` is the site's own section title: the core finds the unit in it ("יחידה 4 - ...").
- `unit_hint` only when the site states the unit and the title doesn't; `"general"` for whole-course items (exam information, past exams, formula sheets).
- Skip URLs already in `site-status`.

Done when: every section has been opened, and every file link in it is an item or already downloaded.

## 4. Recordings: ask first

Count the recording items. Tell the student how many recordings there are and, when the site shows durations, the total hours. Say downloading them is recommended but slow and large. Ask: download all, only unit N, or not now. Recordings not chosen stay listed without a `file`; the core reports them as available.

## 5. Download

Download the chosen files into one new folder under the student's Downloads folder (e.g. `Downloads/unistudent-<course>-<date>`), as `site.md` describes. Set each item's `file` to its downloaded name. Save the listing as `listing.json` in that folder.

## 6. Hand over

Run `us ingest --json "<folder>/listing.json" "<folder>"`. The core moves the files into Raw, sorts them, updates the Wiki, and reports `new`, `changed`, `missing` and `unsorted`.

- `unsorted`: ask one grouped question and record answers with `us assign`.
- `missing`: retry those downloads once, then report them.

## 7. Report

Two lines: what's new since the last sync, and what's waiting (recordings not downloaded, unsorted files). If a unit with a study pack got new material, offer `/unistudent:unit N`.
