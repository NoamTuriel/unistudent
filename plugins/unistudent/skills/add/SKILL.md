---
name: add
description: Add the files in the course's inbox/ to Raw, sort them into units, and update the Wiki.
disable-model-invocation: true
---

`us` means `python3 <this skill's base directory>/../../scripts/us.py`.

1. Run `us courses current` and say which course you're working on. No course → stop and offer `/unistudent:setup`.
2. List `inbox/`. Empty → say so and stop.
3. Ask one question: which of these files are the lecturer's material (official)? Default: none (added). Mention that official material wins when sources disagree.
4. Run `us add --json [--official "<file name>" ...]`.
5. Resolve the `unsorted` files with one grouped question (unit number or "general"); record each with `us assign "<path>" <unit|general>`.
6. The result's `wiki.images` and `wiki.needs_visual` list files with no text layer. Dispatch the `source-reader` subagent for them (one per file) so their content reaches the Wiki.
7. If a unit that got new material has a study pack (`us study changes --unit N --json` shows `has_study_pack: true`), offer `/unistudent:unit N` to review proposed changes.
8. Report in two lines: what was added and where it went.

Done when: the inbox is empty, every added file has a unit or the student deferred it, and scanned files were read.
