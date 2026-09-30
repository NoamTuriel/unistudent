---
name: study-pack
description: Build a study pack for one unit (the student picks the pages), or propose updates to an existing one.
disable-model-invocation: true
---

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

## 1. Course and unit

Run `us courses current` and say which course. Get the unit number from the student's request, or ask.

Done when: you have the course and the unit number.

## 2. Existing pack → propose, never overwrite

If `study/Unit N/` exists, run `us study changes --unit N --json`.

- `has_study_pack` and changes: read the new and changed Wiki pages and draft a change list ("2 new questions for topic 3 from <source>: add them?"). Apply only what the student approves, then run `us study mark-built --unit N`. Stop.
- No changes: say the pack is up to date and ask what they want changed.

Study packs belong to the student: change only what they approve.

Done when: there is no pack yet (go on to step 3), or the student approved or declined every proposed change.

## 3. Resolve the rules

Read, in this order (later wins):

1. the generic rules: `<this skill's base directory>/../../reference/study-pack.md` (or `us doc study-pack`);
2. the field and course skills: if `.unistudent/settings.json` names a `course_skill`, load that skill (it names its field skill; load that too).
   - No `course_skill` set, or it isn't installed: check `us course-skill status --field "<broad field>" --course-name "<course name>" --json` for a previously generated fallback and use it if there is one.
   - Still none: interview the student once — the course's broad academic field, what to emphasize in this course's study packs, and how it wants material summarized. Show back what you're about to save; on confirmation, run `us course-skill save --field "<field>" --course-name "<course>" --emphasis "<summary>" --summarize "<summary>"` and use it from here on. Say plainly this is remembered for next time.
3. general preferences, then `course-preferences.md` (paths in the course context, `.unistudent/context.md`).

Done when: you know the page list, each page's content rules, and the concept structure.

## 4. Pick pages

**Ask** (several answers allowed): every available page with its one-line "what it gives you", all default pages selected. Skip the recordings page when the unit has no transcripts, and say why.

Done when: the student chose the pages.

## 5. Build

**Delegate** to one `study-pack-writer` worker, giving it: course folder, unit, the chosen pages, the resolved rules (paste them in full: the worker can't see your skills), the format (Obsidian or Markdown), and the language.

Done when: the writer returned its page list.

## 6. Verify

**Delegate** `study/Unit N/` to the `verifier` worker. Fix what it reports, then run it again.

Done when: `us check --labels "study/Unit N"` reports 0 problems.

Then run `us study mark-built --unit N`.

## 7. Change requests during the session

Follow "Change requests" in the course context (`.unistudent/context.md`). Save with `us prefs add --scope course|general --text "<the rule>"`.

Done when: every whole-unit change the student asked for is saved at the scope they chose.
