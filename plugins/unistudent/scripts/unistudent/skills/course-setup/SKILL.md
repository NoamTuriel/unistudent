---
name: course-setup
description: Set up a new course folder (onboarding). Run once per course.
disable-model-invocation: true
---

Set up one course for the student, then show them how the plugin works. **Ask** one question per step, recommended option first. The student may be new to Claude: plain words, no jargon.

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## Start: explain the whole process first

Before the first question of a new setup, tell the student the big picture in their language, in plain words, as a short list (a resumed setup gets one line instead: "We're continuing: here's where we are and what's left"):

- **What we're building:** a personal study assistant for this one course. Your course material goes into one organized place (the "Wiki": a hidden set of pages the AI searches, which you never need to open), so it answers from *your* course, not from the whole internet, and marks every paragraph with how far to trust it.
- **The steps (9):** 1. your university (and the plugins that help), 2. your course, 3. your language, 4. where to keep it, 5. fetching your material, 6. sorting it into units, 7. recordings, 8. analyzing it into the Wiki, 9. how to use it.
- **Adding more later is one move:** you'll get an "inbox" folder: drop any new file into it and run `course-add`. Setup shows you again at the end.
- **It takes time, and it's worth it.** Fetching and analyzing are the slow parts, longer for a big course or for recordings. It's done once per course; after that every answer is fast, grounded in your material, and easy to check.
- **Every step comes with its reason.** You may stop at any point and run setup again: it picks up where it stopped.

**Keep the student oriented all the way through.** Setup is long and heavy, so ask **one question at a time** and:

- **Before each step**, say in one line where you are ("Step 5 of 9: fetching your material"), what's about to happen, and whether it will take a while.
- **During a long job** (fetching, building the Wiki, transcribing), say it has started and what you're waiting for. When it finishes, say what happened in one or two lines, and what comes next.
- **After each step**, record it (`us setup-progress advance`, see step 0) and say so once: "Saved: if you close this, run setup again and I'll continue from here."
- **If they come back later or you're resuming**, start with a recap: what's done, what's left, what's next. Don't re-ask anything already recorded.
- **Keep the conversation light.** Do the heavy work in a subagent where you can run subagents (fetching, the Wiki build, recordings): give it the step's instructions, and have it return a short result (what worked, what failed, what was skipped), not logs. Every question to the student stays in this conversation. Installs are one command: run it quietly and read only the last lines of its output. Where you can't run subagents, do the work yourself and keep what you show short.

Done when: the student has seen the overview (or the one-line recap), and none of it needed an unexplained term.

## 0. Resume, if setup was started before

Run `us setup-progress status --course-name "<course, if you already know it>"` once you know the course name (step 2), or `us setup-progress list --json` before that if you don't. An entry whose course name is a university (its `university` answer equals its name) is the placeholder from step 1: resume at step 2 and ask for the course. If there's progress for this course, say so ("Picking up where we left off, after <stage>") and skip straight to the stage after the last one recorded, using the answers already stored instead of asking again. After finishing each numbered stage below, record it: `us setup-progress advance --course-name "<course>" --stage <stage> [--answer key=value ...]` (stage names: `university`, `course`, `language`, `path`, `format`, `fetch`, `sort`, `recordings`, `analyze`, `capabilities`). Progress is kept per course name. The university is asked before the course name is known, so step 1 records it under the university's name as a placeholder, and step 2 moves it to the course's name; the later stages each have their own record line below. Keep the overview's step count (9) equal to the numbered steps below. Recording the last stage (`capabilities`) clears the progress automatically.

## 1. University

Ask which university. Say why in a sentence: the university decides where your official material lives and how it's organized, so the AI knows where to get it and how to sort it.

- A plugin for it is installed (e.g. `openu`): use it; it knows how to reach the course site.
- None installed, but a generated fallback already exists (`us university status --university "<name>" --json` says `generated: true`): reuse it silently — no re-interview.
- Neither: interview them once — ask for the course site's URL and how they organize and prioritize material (by week? by topic? exams and solutions kept separately?). Show back what you're about to save, and on confirmation run `us university save --university "<name>" --url "<url>" --organizing "<summary>"`. Say plainly: this is remembered, so next course at the same university skips this question.

Record the answer right now, before anything else (an install in the next paragraph stops setup): `us setup-progress advance --course-name "<university name>" --stage university --answer university=<name>` (the placeholder name step 0 explains).

Then run `us plugins recommend --university "<name>" --json`. If it returns a plugin you don't already have (you can tell from the sync skills you can see; if you can't tell, say what the plugin is for and how to add it, and don't claim it's missing), say in one plain sentence what it gives them and give its `install` command. Always recommend it, and ask them to install it now, before going on. Say why: a plugin teaches the AI your university's course site (so it can fetch your material for you, from the source, instead of you downloading it by hand). Tell them what happens next in these words: after installing a plugin, **close and reopen (reload) the app**, because plugins are only picked up when it starts, then run setup again; it continues from the university you just gave. Setup resumes right where it stopped. Only if they can't or won't, carry on with the generic rules or the generated fallback, and say plainly what they'll be missing. Nothing returned → say in one sentence that no plugin exists for this yet and the generic rules work for any course; if they aren't using Claude, also give the `other_apps` line.

Done when: `university` is recorded, you know the university and, if relevant, how to reach its site (installed plugin, generated fallback, or "own folder only for now"), and every plugin the command recommended has been recommended, and installed or knowingly declined.

## 2. Course

Ask which course. Say why in a sentence: each course gets its own folder and Wiki, so nothing from another course leaks into your answers.

Record both stages now under the course's name: `us setup-progress advance --course-name "<course>" --stage university --answer university=<name>`, then `--stage course --answer course_name=<course>`; then drop the placeholder from step 1 with `us setup-progress clear --course-name "<university name>"`.

Done when: you have the course name, and `university` and `course` are recorded.

## 3. Language

Ask which language the course folder should speak. Say why in a sentence: it names the folders you'll see, and the units and trust-level folders inside them, in your language; it's also the language of the Wiki's notes, of the answers, and the one recordings are transcribed in. Offer Hebrew and English (recommend the language the course is taught in), or another language they name. Hebrew and English have ready-made folder names; for any other language the folder names are English and everything else still follows their language. Say that plainly, and don't promise translated folder names. Record it: `us setup-progress advance --course-name "<course>" --stage language --answer language=<he|en|other code>`.

Done when: you have a language code and the student knows what it changes, and `language` is recorded.

## 4. Storage and format

Ask where to keep the course folder. Say why in a sentence: everything for the course goes in this one folder (your files, your study packs, and a hidden area for the Wiki the AI reads), so it reads one place and never mixes up courses, and you always know where things are. Suggest `<their documents folder>/University/<course name>`. On a device bridge, request access to that one folder only. Record it: `us setup-progress advance --course-name "<course>" --stage path --answer path=<folder>`.

If the folder is inside iCloud, Google Drive, Dropbox or OneDrive, tell them in one sentence: recordings will be kept in a local folder that doesn't sync, because synced folders push big files to the cloud and can evict them.

Then ask which app they'll read their notes and study packs in, and record that stage too (`--stage format --answer format=<obsidian|markdown> --answer app=<their choice>`) — see step 0. Offer: Obsidian, Word (docx), OneNote, Google Docs, or plain Markdown / something else. Recommend Obsidian, and say why in a sentence: it's the best fit, because it opens the study packs as they are, with working links between pages and callouts: you will open the course's study folder as an Obsidian vault. Obsidian → format `obsidian`. Any other choice → format `markdown` (standard links, PNG graphs): the study packs stay Markdown files, and they copy a finished pack into Word, OneNote or Google Docs, where the PNG graphs paste or insert as pictures. Say that plainly, so they know what to expect, and that they can switch to Obsidian later.

Done when: you have a folder path, a format and the app they'll use, each recorded as its own stage.

## 5. Fetch the material

Ask one question at a time in this step, and say first, in plain words:

- **What we're doing:** gathering your course's *official* material in one place: the lecturer's and university's slides, readings, textbook, exercises, solutions and past exams.
- **Why official only:** the whole point is that the AI answers from *your course*. Official material is what you'll be tested on, with your course's notation and methods. A friend's summary, another university's notes or something from the internet may use a different method or contain mistakes, and then an answer would look like it came from your course when it doesn't. If they also have unofficial material, it's allowed, but it is kept apart as "added", named as such, and never overrides official.
- **Why more is better:** everything the AI can read is something it can cite. Solutions and past exams matter most: they show how the course wants problems solved. So ask for everything the course gave, not just the slides.

Then ask: download from the course website, use a folder they already have, or both.

- A university plugin is installed (step 1): offer all three.
- A generated fallback only (step 1): its notes only record how the university organizes its material (where it lives, what matters); it is not a downloader. Offer to try fetching from the site by following those notes, and the other two.
- **If you can't log in or can't fetch** (no access from this app, a login that needs the student, a site that changed): say so in plain words, say it is not an error and nothing is lost, and move on to the student's own folder or the inbox. Never loop on a failing login.
- Neither a plugin nor a fallback: offer their own folder and the inbox only.
- Own folder: ask for it, and ask whether it is the lecturer's material (official) or other material (added). Tell them it is copied in once and their original files are left exactly where they are; nothing of theirs is moved or changed.

Run `us setup "<folder>" --name "<course>" --format <obsidian|markdown> --language <the language from step 3> [--university <plugin>] [--import "<own folder>" --tier <official|added>]`. Setup creates the three folders the student will see: its result names them (`inbox`, `material`, `study`). Tell the student where the **inbox** is (its name), and that new files go in there later.

If downloading from the site: run the university plugin's sync skill (e.g. `openu:openu-sync`) or, with a generated fallback, fetch using its saved notes. Fetching can be slow: say so up front, and confirm what came in when it's done.

Before moving on, ask once for anything else the course gave them that hasn't come up yet: other books, solution sets, past exams. More material now means better summaries and answers later.

Record it: `us setup-progress advance --course-name "<course>" --stage fetch`.

Done when: the course folder exists, the files the student has (from the site, their folder, or none yet) are in the Material folder, the student knows where the inbox is, and `fetch` is recorded.

## 6. Sort the material into units

Say the step in one line: the AI needs to know which unit (chapter) each file belongs to, so study packs and answers use the right material. Run `us unsorted --json`. If any file has no unit, ask one grouped question (unit number, or "general" for whole-course files such as past exams) and record each answer with `us assign "<path>" <unit|general>`. A recording of a whole class session (judge it from the whole file name and folder names, in any naming scheme) belongs to no unit: propose "Recorded lessons" for it and record it with `us assign "<path>" lessons`. Nothing unsorted → say so in one line and go on.

Record it: `us setup-progress advance --course-name "<course>" --stage sort`.

Done when: `us unsorted` prints "Nothing unsorted." (or the student chose to leave the rest for later), and `sort` is recorded.

## 7. Recordings

Skip this step with one line ("no recordings, so nothing to do here") when the course has none, and record it. Otherwise run `us recordings estimate --json` and ask whether to include them: skip, download only, or "ask me per recording" (the student then picks each transcription by number in `/unistudent:course-recordings`; nothing is transcribed in setup). Say it's recommended but slow, with the numbers, and why it's worth it: a transcript lets the AI answer from what the lecturer said, link to the exact minute, and write down spoken announcements ("this will be on the exam") with the time they were said. Record the choice with `us context --recording-level <0 skip|1 download only|3 ask me per recording, then transcript and summary>`. Transcription itself happens later, in `/unistudent:course-recordings`: point there.

If they want transcripts (3) and `backend_installed` is false, they need a speech-to-text tool, and it isn't part of the plugin. Say so plainly and **recommend installing it now**: it's a separate download that runs on their own computer (large: about a gigabyte or more, with the language model fetched the first time it runs), and nothing is sent anywhere. Then **ask whether to install it for them**. Yes → run `install_run` from the estimate with your shell tool (if you can't run commands, show it for them to run), then run `us recordings estimate --json` again and confirm `backend_installed` is true. If `ffmpeg` is missing too (check with `which ffmpeg`, or `where ffmpeg` on Windows), offer to install it the same way: macOS `brew install ffmpeg`, Windows `winget install ffmpeg`, Linux your package manager. No → record level 1 (download only), and tell them they can add it any time and run `/unistudent:course-recordings`. Tell them too that this install can be lost if the tool that runs UniStudent rebuilds its environment. *For advanced users:* the lasting way is the README's `uv tool install "unistudent[stt] @ ..."`; setup would then simply offer it again.

If they chose transcripts (3), ask about **frame analysis** as its own question (a separate yes/no, never bundled with transcription). Explain it plainly first:
- **What it gives:** a transcript only has the words. Lecturers also show diagrams, graphs, formulas and slides on screen, and say "as you can see here". Frame analysis looks at the video, so those pictures and formulas end up in the recording's summary, linked to the minute they appeared, instead of being lost.
- **What it needs:** a video-analysis tool next to UniStudent (the README suggests `mcp-video-analyzer`) and `ffmpeg`. It isn't part of the plugin. Check whether you can see such a tool; if not, say so and offer to explain how to add it.
- **How heavy it is:** the slowest and most expensive part: one extra AI call for roughly every minute of video (`frame_analysis_segments` in the estimate gives the real number for their recordings), on top of transcription. Say the number and that it's optional: transcripts alone are already useful.
- **Recommend it** for courses whose lecturer teaches from drawn graphs or slides (economics, maths, science); fine to skip for talking-only lectures.

Tool available and they say yes → `us context --frame-analysis 1`. Say no, or no tool yet → `us context --frame-analysis 0`, and tell them they can turn it on later in `/unistudent:course-recordings` once the tool is installed (never turn it on without the tool).

Record it: `us setup-progress advance --course-name "<course>" --stage recordings --answer recording_level=<0|1|3>`.

Done when: the recording level is recorded (or the course has no recordings), if they chose transcripts the speech-to-text tool is installed (or they chose download only), frame analysis was asked once and recorded (on or off), and `recordings` is recorded.

## 8. Analyze (build the Wiki)

Tell the student in plain words what's about to happen and why: the AI reads all the material you gathered and turns it into the Wiki, a knowledge base of its own: one page per unit, a glossary, a bank of questions, and a source page for each file. Why: an AI can't hold a whole course in its head, and re-reading every file each time is slow and error-prone. With the Wiki it finds the right place at once, answers from your material, and can point back to the exact page or moment, instead of guessing. Say honestly that this can take a while, and that it is done once: later additions are added without starting over.

Read `<this skill's base directory>/../course-wiki/SKILL.md` and follow it for the whole course. Then run `us context --exam-date <date>` if the student knows the exam date (ask once; skipping is fine).

Then show the student what was and wasn't analyzed. Do it here, after the files are fetched, sorted and built, never before: until the first build every file reads "pending" (not read yet), which is true but alarming. Run `us wiki coverage --json` and tell them the counts (analyzed, failed, skipped, still pending) in plain words (after the build, "pending" can only be recordings still waiting for their transcript: say that), and name each failed or skipped file with its reason and what to do about it (for example "this PDF has no text layer: I can read it visually if you want", "these recordings were skipped at your choice: run `/unistudent:course-recordings` any time"). Ask what to do about any gap worth fixing. The same list is saved as `coverage.md` in the Wiki (in the hidden `.unistudent` folder), so any later session knows what is not in the Wiki. Record it: `us setup-progress advance --course-name "<course>" --stage analyze`.

Done when: `us wiki check` reports 0 problems, the student has seen the coverage summary, and `analyze` is recorded.

## 9. Capabilities: explain, then show, what this can do

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
