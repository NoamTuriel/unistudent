---
name: course-setup
description: Set up a new course folder (onboarding). Run once per course.
disable-model-invocation: true
---

Set up one course for the student, then show them how the plugin works. Setup asks every question first (steps 1 to 8), then runs on its own for hours without asking anything (step 9), then reports (steps 10 and 11). **Ask** one question per step, recommended option first. The student may be new to Claude: plain words, no jargon.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); as the Claude plugin, give them to the plugin's subagent of that name, which has the UniStudent tools (in parallel when there are several); in any other app, follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## Start: explain the whole process first

Before the first question of a new setup, tell the student the big picture in their language, in plain words, as a short list (a resumed setup gets one line instead: "We're continuing: here's where we are and what's left"):

- **What we're building:** a personal study assistant for this one course. Your course material goes into one organized place (the "Wiki": a hidden set of pages the AI searches, which you never need to open), so it answers from *your* course, not from the whole internet, and marks every paragraph with how far to trust it.
- **How long:** about 10 minutes of questions, then you can leave for a few hours. Then 5 to 10 minutes to log in and approve what gets downloaded, then the slow part runs on its own (downloading, reading, transcribing recordings), then about 5 minutes when you come back.
- **The steps (11):** 1. your university, 2. your course, 3. your language, 4. where to keep it and how you'll read it, 5. your material and exam date, 6. recordings, 7. creating the folder and installing, 8. approving the download, 9. the long run (you can leave), 10. your report, 11. how to use it.
- **Adding more later is one move:** you'll get an "inbox" folder: drop any new file into it and run `course-add`. Setup shows you again at the end.
- **It takes time once, and it's worth it.** After that every answer is fast, grounded in your material, and easy to check. You may stop at any point and run setup again: it picks up where it stopped.

**Keep the student oriented all the way through:**

- **Before each step**, say in one line where you are ("Step 5 of 11: your material"), and why the question matters, in one sentence.
- **After each step**, record it (`us setup-progress advance`, see step 0) and say so once: "Saved: if you close this, run setup again and I'll continue from here."
- **Keep the conversation light.** Do the heavy work in a subagent where you can run subagents (the sync, the Wiki build, recordings): give it the step's instructions, and have it return a short result (what worked, what failed, what was skipped), not logs. Every question to the student stays in this conversation, and all of them come before step 9. Installs are one command: run it quietly and read only the last lines of its output.

Done when: the student has seen the overview (or the one-line recap), and none of it needed an unexplained term.

## 0. Resume, if setup was started before

Run `us setup-progress status --course-name "<course, if you already know it>"` once you know the course name (step 2), or `us setup-progress list --json` before that if you don't. An entry whose course name is a university (its `university` answer equals its name) is the placeholder from step 1: resume at step 2 and ask for the course. If there's progress for this course, say so ("Picking up where we left off, after <stage>") and go to the step for its `next_stage`, using the answers already stored instead of asking again: `course` → 2, `language` → 3, `path` and `format` → 4, `material` → 5, `recordings` → 6, `installs` → 7, `plan` → 8, `run` → 9, `capabilities` → 10. After finishing each step, record it: `us setup-progress advance --course-name "<course>" --stage <stage> [--answer key=value ...]`. Progress is kept per course name; the answers of steps 5 and 6 wait there until step 7 creates the course folder. A progress file from an older setup (stages `fetch`, `sort`, `analyze`) is read as the matching new stage by the command itself, but may lack answers the new steps ask for: when `us setup-progress status` lists `missing_answers`, ask only those questions (one at a time, as worded in steps 5 and 6: `source` is step 5's material question, `transcribe`, `frame_analysis` and `keep_video` are step 6's three Recording questions), record them with `--answer`, and only then go on to step 7. Never guess a missing answer, `keep_video` least of all. Keep the overview's step count (11) equal to the numbered steps below. Recording the last stage (`capabilities`) clears the progress automatically.

## 1. University

Ask which university. Say why in a sentence: the university decides where your official material lives and how it's organized, so the AI knows where to get it and how to sort it.

Record the answer right away: `us setup-progress advance --course-name "<university name>" --stage university --answer university=<name>` (the placeholder name step 0 explains).

- None, "I'm learning on my own, no university" (offer this answer in plain words): record `university=none`, then skip the plugin recommendation and the interview: there is no course site to reach. Everything else works the same.
- Otherwise run `us plugins recommend --university "<name>" --json`.
  - It returns a plugin you already have (you can see its sync skill, e.g. `openu`): use it; it knows how to reach the course site.
  - It returns a plugin you don't have: say in one plain sentence what it gives (it teaches the AI your university's course site, so it can fetch your material for you), and recommend it. Say that it is recorded, not installed yet: it is installed in step 7 together with anything else that needs the app restarted, so you restart at most once, after all the questions. Yes → record it the same way with `--answer plugin=<name>` added. If you can't tell whether it's installed, say what it is for and don't claim it's missing. No → carry on, and say plainly what they'll be missing.
  - Nothing returned: say in one sentence that no plugin exists for this yet and the generic rules work for any course; if they aren't using Claude, also give the `other_apps` line. Then: a generated fallback already exists (`us university status --university "<name>" --json` says `generated: true`) → reuse it silently, no re-interview. None → interview them once: the course site's URL and how they organize and prioritize material (by week? by topic? exams and solutions kept separately?). Show back what you're about to save, and on their OK run `us university save --university "<name>" --url "<url>" --organizing "<summary>"`. Say plainly: this is remembered, so the next course at the same university skips this question.

Done when: `university` is recorded (with `plugin` when one is to be installed), and you know how the site will be reached: a plugin (installed or to be installed in step 7), a generated fallback, or no site.

## 2. Course

Ask which course. Say why in a sentence: each course gets its own folder and Wiki, so nothing from another course leaks into your answers.

Record both stages now under the course's name: `us setup-progress advance --course-name "<course>" --stage university --answer university=<name> [--answer plugin=<name>]`, then `--stage course --answer course_name=<course>`; then drop the placeholder from step 1 with `us setup-progress clear --course-name "<university name>"`.

Done when: you have the course name, and `university` and `course` are recorded.

## 3. Language

Ask which language the course folder should speak. Say why in a sentence: it names the folders you'll see, and the units and trust-level folders inside them, in your language; it's also the language of the Wiki's notes, of the answers, and the one recordings are transcribed in. Offer Hebrew and English (recommend the language the course is taught in), or another language they name. Hebrew and English have ready-made folder names; for any other language the folder names are English and everything else still follows their language. Say that plainly, and don't promise translated folder names. Record it: `us setup-progress advance --course-name "<course>" --stage language --answer language=<he|en|other code>`.

Done when: you have a language code and the student knows what it changes, and `language` is recorded.

## 4. Where to keep it, and how you'll read it

Ask where to keep the course folder. Say why in a sentence: everything for the course goes in this one folder (your files, your study packs, and a hidden area for the Wiki the AI reads), so it reads one place and never mixes up courses. Suggest `<their documents folder>/University/<course name>`. On a device bridge, request access to that one folder only. Record it: `us setup-progress advance --course-name "<course>" --stage path --answer path=<folder>`. If the folder is inside iCloud, Google Drive, Dropbox or OneDrive, tell them in one sentence: recordings will be kept in a local folder that doesn't sync, because synced folders push big files to the cloud and can evict them.

Then ask which app they'll read their notes and study packs in. Offer: Obsidian, Word (docx), OneNote, Google Docs, or plain Markdown / something else. Recommend Obsidian, and say why in a sentence: it opens the study packs as they are, with working links between pages and callouts. Obsidian → format `obsidian`. Any other choice → format `markdown` (standard links, PNG graphs): the study packs stay Markdown files, and they copy a finished pack into Word, OneNote or Google Docs, where the graphs paste as pictures. Say that plainly, and that they can switch to Obsidian later. Record it: `us setup-progress advance --course-name "<course>" --stage format --answer format=<obsidian|markdown> --answer app=<their choice>`.

Done when: you have a folder path, a format and the app they'll use, each recorded as its own stage.

## 5. Your material, and the exam date

Say first, in plain words:

- **What we're gathering:** your course's *official* material in one place: the lecturer's and university's slides, readings, textbook, exercises, solutions and past exams.
- **Why official only:** the AI should answer from *your course*: its notation, its methods, what you'll be tested on. A friend's summary or something from the internet may use a different method or contain mistakes. Other material is allowed, but it is kept apart as "added", named as such, and never overrides official.
- **Why more is better:** everything the AI can read is something it can cite. Solutions and past exams matter most: they show how the course wants problems solved.

Ask where the material comes from:

- A University plugin (installed, or to be installed in step 7): the course website, a folder they already have, both, or nothing yet.
- A generated fallback only: the same choices; say the website is tried by following its saved notes, and may not work.
- Neither: a folder they already have, or nothing yet (they'll drop files in the inbox later).
- No university (`none`, step 1): offer "my own folder" and "nothing yet" only, and setup passes `--university none` to `us setup` in step 7.
- Their own folder: ask which folder, and whether it is official or added: the lecturer's and university's material (official), or other material (added). Tell them it is copied in once and their original files stay exactly where they are; nothing of theirs is moved or changed. Step 7 tells them how many files and how much that is.

Then ask once for anything else the course gave them that hasn't come up: other books, solution sets, past exams. They can add it now to their folder, or later through the inbox.

Then ask for the exam date, if they know it (optional: skipping is fine). It tells the AI how much time is left when planning.

Record it: `us setup-progress advance --course-name "<course>" --stage material --answer source=<site|own|both|none> [--answer own_folder=<folder> --answer tier=<official|added>] [--answer exam_date=<YYYY-MM-DD>]`.

Done when: you know where the material comes from (and the folder and its trust level, for their own folder), they were asked about anything else and the exam date, and `material` is recorded.

## 6. Recordings

Say why in a sentence: recorded lessons hold what the lecturer *said*: explanations, worked examples, and spoken announcements ("tell me next week who you're working with", "this will be on the exam") that appear nowhere else. Ask these three questions even if they don't know yet whether the course has recordings: the answers apply to whatever recordings come in. Each is its own question; one answer never decides another. Costs are rough until this computer is measured.

**Question 1 of 3: transcribe and summarise the recordings?** Recommended.
- **What it gives:** a written transcript of each recording, and a summary with a table of contents that links every topic, example and announcement to the exact minute it was said. The AI can then answer from what the lecturer said.
- **What it costs, per hour of recording:** about 10 minutes of this computer's time on a Mac with Apple silicon, about 30 minutes on other computers; almost no disk; some Claude usage, to read the transcript and write the summary. It needs a free speech-to-text tool on this computer (downloaded once: about 1.6 GB, or about 3 GB for Hebrew on a Mac; it runs here and sends nothing anywhere).
- Ask yes or no. The recordings you approve in step 8's download list are transcribed then: you won't be asked again recording by recording. No → they are still downloaded (sound only, if you don't keep the video), so you can have them transcribed any time later with `/unistudent:course-recordings`.

**Question 2 of 3: frame analysis (looking at the screen)?** Recommended for courses taught from slides, graphs, formulas or drawings (economics, maths, science); fine to skip for talking-only lectures.
- **What it gives:** a transcript has only the words. When the lecturer says "as you can see here", frame analysis looks at the video at that moment, so the slide, graph or formula ends up in the summary, linked to the minute.
- **What it costs, per hour of recording:** about 60 extra AI calls (one per minute of video), on top of question 1. This uses a lot of your Claude usage: on a smaller Claude plan the run may pause at your usage limit; it continues when you run setup again. It needs a free video-analysis tool next to UniStudent, installed in step 7.
- Ask yes or no, only if they said yes to question 1 (it works on the transcript); otherwise record no.

**Question 3 of 3: keep the video files to watch?** Recommended, if the disk has room.
- **What it gives:** the recordings stay on your computer as videos you can watch. Without them, a sound-only copy is kept, so every "said at 42:10" link in the summaries still opens the right minute.
- **What it costs, per hour of recording:** about 0.8 GB of disk for the video (less than 0.1 GB for sound only), and about 5 minutes of download. No Claude usage.
- Ask yes or no.

Then, when they said yes to question 1, ask for their consent to install, during the long run, what the recordings need and this computer doesn't have yet: the speech-to-text tool, and ffmpeg (a free tool that reads and cuts audio and video). Say both are free and run on their computer. No → recordings are downloaded but not transcribed (record question 1 as no).

Record it: `us setup-progress advance --course-name "<course>" --stage recordings --answer transcribe=<yes|no> --answer frame_analysis=<yes|no> --answer keep_video=<yes|no> --answer installs=<yes|no>`.

Done when: each of the three questions was asked on its own with what it gives, its cost and the recommendation, consent to the installs was asked when transcripts are wanted, and `recordings` is recorded.

## 7. Create the course folder, and install what needs a restart

No more questions about the course after this. First create the course folder, so every install can write into it:

1. Run `us setup "<folder>" --name "<course>" --format <obsidian|markdown> --language <language> [--university <plugin, or none>]`. Its result names the three folders (`inbox`, `material`, `study`). Tell the student where the **inbox** is, and that new files go in there later.
2. Apply the stored answers: `us context --recording-level <3 if transcribe, else 1> --frame-analysis <1|0> --keep-video <1|0> [--exam-date <date>]`.
3. Their own folder (step 5): run `us import --dry-run "<own folder>" --tier <official|added>` and say its one-line `summary` (how many files and how much will be copied). Nothing is copied yet.

Then install, all together, what only works after the app is restarted:

- **The University plugin** recorded in step 1: install it with its `install` command if your app lets you, otherwise give the student that command to run.
- **The video-analysis tool**, when frame analysis is on and you can't see such a tool yet: set up the `mcp-video-analyzer` MCP server (its start command is on https://github.com/guimatheus92/mcp-video-analyzer) the way the generic rules' "Recommended tools" section says (its Harness table: `<this skill's base directory>/../../reference/study-pack.md`, or `us doc study-pack`): in the course folder's own MCP config file where your app reads one, otherwise name it and give the exact steps. If it can't be set up, run `us context --frame-analysis 0` and say so in one sentence.

Record it before any restart: `us setup-progress advance --course-name "<course>" --stage installs`. If anything was installed above, say once, plainly: "Please close and reopen the app (where it reads the course folder's settings, open it in the course folder), then run setup again: it continues from here." Nothing installed → say so in one line and go straight on.

Done when: the course folder exists, the recording and exam answers are applied, their own folder's one line was said, every restart install is done or knowingly skipped, at most one restart was asked for, and `installs` is recorded.

## 8. Before downloading: approve the Fetch plan

Say what's about to happen: the course site is scanned without downloading anything, you'll see what would be downloaded, how big it is and how long it takes, and nothing downloads until you say OK. This takes 5 to 10 minutes.

- **From the course website, with a University plugin:** ask them to open Chrome and log in to the course site (never ask for or type their password). Then run the plugin's sync skill (e.g. `openu:openu-sync`) and tell it that it runs inside setup: it scans the site, shows the Fetch plan with its three choices (download all, skip all recordings, edit the list, in the chat or in the checklist file, showing the updated plan after each change), waits for an explicit OK, and asks one grouped question about files whose unit it can't tell: a unit, general, or "I don't know" (left unsorted, but still read into the Wiki). It stops there; its download runs in step 9.
- **From the course website, with a generated fallback:** its notes only record how the university organizes its material; it is not a downloader. Follow those notes to list the course files in the same listing form a University plugin hands over (`{"course_site": ..., "items": [...]}`, one item per file: `url`, `name`, `section`, `kind`, and `size` or `seconds` when shown), save it, and run the same Fetch plan: `us fetch-plan show --json "<listing>"`, the three choices, the explicit OK, the grouped unit question, then `us fetch-plan apply --json "<listing>" [--unit NUMBER=UNIT ...]` (`unknown` for "I don't know").
- **If you can't log in or can't reach the site** (no access from this app, a login that needs the student, a site that changed): say so in plain words, say it is not an error and nothing is lost, and go on with their own folder or the inbox. Never loop on a failing login.
- **Their own folder:** run `us import "<own folder>" --tier <official|added>` now (it only copies). If they said yes to transcripts, approve its recordings for transcription: `us recordings approve "<path>" ...` with every path in `us recordings list` (their yes in step 6 is the approval). Then `us unsorted --json`: if any document has no unit, ask one grouped question: a unit number, general (whole-course files such as past exams), or "I don't know" (left unsorted, still read into the Wiki). Record each answer with `us assign "<path>" <unit|general>`. Recordings are sorted in step 9.

Then run `us fetch-plan status --json` and show its `box` exactly as it comes, in a code block; if its `box` is empty (nothing to download), say the run will be short instead. Tell them, in plain words, that they can leave now and come back in about the time it shows, and that the run asks them nothing.

Record it: `us setup-progress advance --course-name "<course>" --stage plan`.

Done when: every download was approved with an explicit OK (or there is nothing to download), every file without a unit has an answer (or "I don't know"), the student has seen the box, and `plan` is recorded.

## 9. The run: the student can leave

From here to step 10 there are no questions: the student is away. A step that fails is tried once more; if it fails again, skip it, note what failed and what the student can do about it for the report, and go on. Between parts, post a progress message: the `box` from `us fetch-plan status` exactly as it comes, in a code block (when there is one), and one line saying what's next. If the run stops (usage limit, the app closed, the computer slept), the student will run setup again: step 0 sends them back here, and every part below skips what's already done.

1. **Installs**, when they consented in step 6: run `us recordings estimate --json`; if `backend_installed` is false, run its `install_run` with your shell tool. If ffmpeg is missing (`which ffmpeg`, or `where ffmpeg` on Windows): macOS `brew install ffmpeg`, Windows `winget install ffmpeg`, Linux the package manager. Speech-to-text still missing after the second try → `us context --recording-level 1` (recordings are downloaded, not transcribed) and put it in the report with the command to run later. If you can't run commands, the same, with the commands in the report.
2. **Documents first, then the Wiki on them**, so the Wiki is usable early: with a University plugin, its sync's document download and ingest, from the approved listing; with a generated fallback, download each approved document from the approved listing that `us site-status` doesn't list yet into one folder and run `us ingest --json "<approved listing>" "<that folder>"`. Their own folder was copied in step 8. Then read `<this skill's base directory>/../course-wiki/SKILL.md` and follow it for the whole course (workers in parallel where you can run them).
3. **Recordings, in parallel with step 2** where you can run subagents (otherwise after it), for those the plan approved:
   - Download them with the sync's recording download, one at a time, oldest first (it keeps sound only when the Settings say so).
   - Transcribe in the background: every recording whose line in `us recordings list` reads `none` (no transcript yet), with `us recordings transcribe "<path>" ... --background`. It goes oldest first, so the first units are usable within the first hour. Check `us recordings list` between other work.
   - As soon as a transcript lands (its line reads `partial`), **delegate** it to one `recording-summarizer` worker; don't wait for the other transcripts, telling it explicitly whether frame analysis is on (`frame_analysis` in `.unistudent/settings.json`: on only if `true`).
   - Frame analysis on and `keep_video` false: once a recording's summary is written, run `us recordings audio-only "<path>"` (the video is replaced by a sound-only copy under the same name, so the time links still work).
   - Where each recording belongs, as in `<this skill's base directory>/../course-recordings/SKILL.md` step 5: a whole class session goes to Recorded lessons (`us assign "<path>" lessons`); a recording that solves one question stays in its unit. One you can't judge from its name and the start of its transcript stays where the site put it and is named in the report.
4. **Final Wiki update:** `us wiki build`, then **delegate** each unit in its `units_touched` to one `wiki-unit-writer` worker (it merges its own glossary and question-bank entries), then `us wiki check` until it reports 0 problems.

Record it: `us setup-progress advance --course-name "<course>" --stage run`.

Done when: every approved file is in the Wiki or noted as failed, every approved recording is transcribed and summarised or noted as failed, `us wiki check` reports 0 problems, and `run` is recorded.

## 10. Coming back: the report

The student is back. Give one short report, in plain words:

- **What's in:** documents and recordings added, units with material.
- **What failed, and what to do:** each failed download, install or recording, with the one thing to do about it (for example "this recording's link expired: run the sync again", "speech-to-text didn't install: run this command, then `/unistudent:course-recordings`").
- **Files you answered "I don't know" for:** they are unsorted but already in the Wiki; they can sort them any time by asking.

Then run `us wiki coverage --json` and give the counts (analyzed, failed, skipped, still pending) in plain words ("pending" after the run can only be recordings still waiting for a transcript: say that), and name each failed or skipped file with its reason and what to do (for example "this PDF has no text layer: I can read it visually if you want"). The same list is saved as `coverage.md` in the Wiki, so any later session knows what's missing. Ask one question: which of these gaps are worth fixing now. Do what they choose, or leave it.

Done when: the student has seen the report and the coverage summary, and answered the one question about gaps.

## 11. Capabilities: explain, then show, what this can do

Explain in the student's language, in a few short lines, following the course folder's `README.md`, using the real folder names from `us courses current`: the folders and the warning on anything not from the course material (⚠️ in words).

Then, in plain words (no unexplained "MCP", "context file" or "grounding" without a one-clause gloss), cover each of these every time, not only if asked:

- **The folders:** two at setup, the inbox (drop new files here; it is emptied once they're added), the Material folder (the real files of the course, in `official` and `added` folders, then by unit; they may move, rename or delete files there, and moving a file between official and added changes how far it's trusted), and, once they first ask for a study pack, a third: the study folder (their **Study vault**; tell them it will appear then, so an absent folder is not a surprise: open that folder as a vault in Obsidian, or in their other app; it holds only what was made for them to study from: study packs and a recordings roadmap per unit). Everything else is in a hidden `.unistudent` folder they never need to open.
- **Deleting in the Material folder deletes the only copy:** there is no second copy. The computer's Trash can bring a file back, so use it carefully. (Files imported from their own folder were copied: those originals are still where they were.)
- **Adding more material later:** drop new files in the inbox, then run `/unistudent:course-add` (or just mention it: Claude will notice next time). Say it again here even though the overview mentioned it: it is the move they will use most.
- **Picking the course up in a new AI session:** say the one sentence that is true for their app, and only that one. Claude Code, Cursor, Codex, Gemini CLI, VS Code: "Open the app inside this course folder and it knows your course." Claude Desktop chat (it reads no folder; the tool is `course_context`, the same as the `us course-context` command): "Create a Project once, and paste this as its instructions: *Start each chat by calling the unistudent course_context tool.* After that every chat starts on your course (this needs the unistudent connector turned on in Desktop; if you have several courses, it asks which one, or use the active one you last switched to)." Cowork: "Choose this course folder when you start a task" (check it works with them before promising; if it doesn't, give the fallback). Say plainly that an app opened *outside* the course folder won't know the course. The last-resort fallback for any app: paste `Read AGENTS.md in <course folder path> before answering.`

Then suggest one concrete next step, chosen from what's actually true for this course (not a generic list) — e.g. "Unit 1 has material ready; want a study pack for it?" or "There are 3 recordings — want a roadmap of what's covered in each?" — and only after that, offer the rest of the commands from the course folder's `README.md` table (and the university plugin's sync skill, if there is one).

In Cowork, suggest one project per course with this folder connected. In Claude Code, suggest starting Claude inside the folder.

Recording this last stage (`us setup-progress advance --course-name "<course>" --stage capabilities`) finishes setup and clears the saved progress.

Done when: the student has seen the explanation, both plain-language points above, a concrete suggestion, and the other commands, and `capabilities` is recorded.
