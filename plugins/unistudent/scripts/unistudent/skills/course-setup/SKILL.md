---
name: course-setup
description: Set up a new course folder (onboarding). Run once per course.
disable-model-invocation: true
---

Set up one course for the student, then show them how the plugin works. **Ask** one question per step, recommended option first. The student may be new to Claude: plain words, no jargon.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. Course

Ask which course. Offer the installed course skills by name (skills whose description starts with "Course skill:", e.g. `economics:macro`), plus "My course isn't listed". Not listed → generic rules; record no course skill.

Done when: you have the course name and the course skill (or none).

## 2. Storage and format

Ask where to keep the course folder and whether they use Obsidian or plain Markdown. Suggest `<their documents folder>/University/<course name>`. On a device bridge, request access to that one folder only.

If the folder is inside iCloud, Google Drive, Dropbox or OneDrive, tell them in one sentence: recordings will be kept in a local folder that doesn't sync, because synced folders break links and push big files to the cloud.

Done when: you have a folder path and a format.

## 3. Source

Ask: download from the course website, use a folder they already have, or both.

- A university plugin is installed (e.g. `openu`): offer all three.
- None installed: offer their own folder and the inbox only, and say downloading needs their university's plugin.
- Own folder: ask for it, and ask whether it is the lecturer's material (official) or other material (added).

Done when: you know the source mode, and the folder and tier if one was given.

## 4. Create the course folder

Run `us setup "<folder>" --name "<course>" --format <obsidian|markdown> --language <he|en> --origin-mode <site|own-folder|both> [--course-skill <skill>] [--university <plugin>] [--import "<own folder>" --tier <official|added>]`.

Then resolve unsorted files: run `us unsorted --json`. If any, ask one grouped question (unit number, or "general" for whole-course files such as past exams) and record each answer with `us assign "<path>" <unit|general>`.

Done when: `us unsorted` prints "Nothing unsorted." or the student chose to leave the rest for later.

## 5. Download from the site (site or both)

Run the university plugin's sync skill (e.g. `openu:openu-sync`). It asks about recordings itself.

Done when: the sync reported what it downloaded.

## 6. Recordings

If the course has recordings and they weren't handled in step 5, run `us recordings estimate --json` and ask whether to include them. Say it's recommended but slow, with the numbers. Record the choice with `us context --recording-level <0 skip|1 download only|3 transcript and summary>`. Transcription itself happens later, in `/unistudent:course-recordings`: point there.

Done when: the recording level is recorded.

## 7. Wiki

Read `<this skill's base directory>/../course-wiki/SKILL.md` and follow it for the whole course. Then run `us context --exam-date <date>` if the student knows the exam date (ask once; skipping is fine).

Done when: `us wiki check` reports 0 problems.

## 8. Explain and offer next steps

Explain in the student's language, in five short lines, following the course folder's `README.md`: what each folder is, the inbox, and the grounding labels (✅ ⚠️ ❌). Then offer the menu:

- Build a study pack for a unit (`/unistudent:study-pack`)
- Process recordings (`/unistudent:course-recordings`)
- Add more material (`/unistudent:course-add`)
- Sync the course site (university plugin)

In Cowork, suggest one project per course with this folder connected. In Claude Code, suggest starting Claude inside the folder.

Done when: the student has seen the explanation and the menu.
