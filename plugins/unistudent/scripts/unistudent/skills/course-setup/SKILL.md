---
name: course-setup
description: Set up a new course folder (onboarding). Run once per course.
disable-model-invocation: true
---

Set up one course for the student, then show them how the plugin works. **Ask** one question per step, recommended option first. The student may be new to Claude: plain words, no jargon.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 0. Resume, if setup was started before

Run `us setup-progress status --course-name "<course, if you already know it>"` once you know the course name (step 2), or `us setup-progress list --json` before that if you don't. If there's progress for this course, say so ("Picking up where we left off, after <stage>") and skip straight to the stage after the last one recorded, using the answers already stored instead of asking again. After finishing each numbered stage below, record it: `us setup-progress advance --course-name "<course>" --stage <stage> [--answer key=value ...]` (stage names: `university`, `course`, `path`, `format`, `fetch-and-organize`, `analyze`, `capabilities`). Recording the last stage (`capabilities`) clears the progress automatically.

## 1. University

Ask which university.

- A plugin for it is installed (e.g. `openu`): use it; it knows how to reach the course site.
- None installed, but a generated fallback already exists (`us university status --university "<name>" --json` says `generated: true`): reuse it silently — no re-interview.
- Neither: interview them once — ask for the course site's URL and how they organize and prioritize material (by week? by topic? exams and solutions kept separately?). Show back what you're about to save, and on confirmation run `us university save --university "<name>" --url "<url>" --organizing "<summary>"`. Say plainly: this is remembered, so next course at the same university skips this question.

Then run `us plugins recommend --university "<name>" --json`. If it returns a plugin you don't already have (you can tell from the course skills and sync skills you can see; if you can't tell, say what the plugin is for and how to add it, and don't claim it's missing), say in one plain sentence what it gives them and give its `install` command. Always recommend it, and ask them to install it now, before going on: it makes setup better (for example, downloading their material for them), and setup resumes right where it stopped once they've installed it and run setup again. Only if they can't or won't, carry on with the generic rules or the generated fallback, and say plainly what they'll be missing. Nothing returned → say nothing about plugins.

Done when: you know the university and, if relevant, how to reach its site (installed plugin, generated fallback, or "own folder only for now"), and every plugin the command recommended has been recommended, and installed or knowingly declined.

## 2. Course

Ask which course. Offer the installed course skills by name (skills whose description starts with "Course skill:", e.g. `economics:macro`), plus "My course isn't listed". Not listed → generic rules; record no course skill.

Once you have the course name, run `us plugins recommend --university "<name>" --course-name "<course>" --field "<field, if you know it>" --json` and give the student one combined list of every recommended plugin they don't already have, each with what it gives them and its `install` command, plus the `other_apps` line if they aren't using Claude. Repeat any from step 1 they haven't installed yet. Always recommend installing them now, before going on (then setup resumes here); only if they can't or won't, carry on with the generic rules and say what they'll be missing.

Done when: you have the course name and the course skill (or none), and the student has been told which plugins fit their university and course (or that none do).

## 3. Storage and format

Ask where to keep the course folder. Suggest `<their documents folder>/University/<course name>`. On a device bridge, request access to that one folder only. Record it: `us setup-progress advance --course-name "<course>" --stage path --answer path=<folder>`.

If the folder is inside iCloud, Google Drive, Dropbox or OneDrive, tell them in one sentence: recordings will be kept in a local folder that doesn't sync, because synced folders break links and push big files to the cloud.

Then ask which app they'll read their notes and study packs in, and record that stage too (`--stage format --answer format=<obsidian|markdown> --answer app=<their choice>`) — see step 0. Offer: Obsidian, Word (docx), OneNote, Google Docs, or plain Markdown / something else. Recommend Obsidian, and say why in a sentence: it's the best fit, because it opens the Wiki and study packs as they are, with working links between pages and callouts. Obsidian → format `obsidian`. Any other choice → format `markdown` (standard links, PNG graphs): the study packs stay Markdown files, and they copy a finished pack into Word, OneNote or Google Docs, where the PNG graphs paste or insert as pictures. Say that plainly, so they know what to expect, and that they can switch to Obsidian later.

Done when: you have a folder path, a format and the app they'll use, each recorded as its own stage.

## 4. Fetch and organize material

Ask: download from the course website, use a folder they already have, or both.

- A university plugin or a generated fallback is available (step 1): offer all three.
- Neither: offer their own folder and the inbox only.
- Own folder: ask for it, and ask whether it is the lecturer's material (official) or other material (added).

Run `us setup "<folder>" --name "<course>" --format <obsidian|markdown> --language <he|en> [--course-skill <skill>] [--university <plugin>] [--import "<own folder>" --tier <official|added>]`.

Then resolve unsorted files: run `us unsorted --json`. If any, ask one grouped question (unit number, or "general" for whole-course files such as past exams) and record each answer with `us assign "<path>" <unit|general>`.

If downloading from the site: run the university plugin's sync skill (e.g. `openu:openu-sync`) or, with a generated fallback, fetch using its saved notes. Fetching can be slow — say so up front, and confirm what came in when it's done.

Before moving on, ask once for anything else the course gave them that hasn't come up yet: other books, solution sets, past exams, anything else from the university. More material now means better summaries and answers later.

Then, if the course has recordings, run `us recordings estimate --json` and ask whether to include them. Say it's recommended but slow, with the numbers. Record the choice with `us context --recording-level <0 skip|1 download only|3 transcript and summary>`. Transcription itself happens later, in `/unistudent:course-recordings`: point there.

Done when: `us unsorted` prints "Nothing unsorted." (or the student chose to leave the rest for later), and the recording level is recorded.

## 5. Analyze (build the Wiki)

Tell the student, in one or two plain sentences, what's about to happen and why: their files (PDFs, slides, recordings) are being turned into a knowledge base Claude can search and cite precisely, instead of Claude re-reading whole documents every time — faster answers, and answers it can point back to a specific page or moment instead of guessing.

Read `<this skill's base directory>/../course-wiki/SKILL.md` and follow it for the whole course. Then run `us context --exam-date <date>` if the student knows the exam date (ask once; skipping is fine).

Done when: `us wiki check` reports 0 problems.

## 6. Capabilities: explain, then show, what this can do

Explain in the student's language, in five short lines, following the course folder's `README.md`: what each folder is, the inbox, and the grounding labels (✅ ⚠️ ❌).

Then, in plain words (no unexplained "MCP", "context file" or "grounding" without a one-clause gloss), cover both of these every time, not only if asked:

- **Adding more material later:** drop new files in the course folder's `inbox`, then run `/unistudent:course-add` (or just mention it — Claude will notice next time).
- **Reconnecting a new AI session:** open the AI app (any of them — Claude Code, Cowork, Cursor, etc.) inside this course folder and it picks the course up automatically. If it doesn't, or the session isn't rooted in the folder, paste this one line: `Read AGENTS.md in <course folder path> before answering.`

Then suggest one concrete next step, chosen from what's actually true for this course (not a generic list) — e.g. "Unit 1 has material ready; want a study pack for it?" or "There are 3 recordings — want a roadmap of what's covered in each?" — and only after that, offer the rest of the commands from the course folder's `README.md` table (and the university plugin's sync skill, if there is one).

In Cowork, suggest one project per course with this folder connected. In Claude Code, suggest starting Claude inside the folder.

Done when: the student has seen the explanation, both plain-language points above, a concrete suggestion, and the other commands.
