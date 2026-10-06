---
name: course-add
description: Move the files in the course's inbox into the Material folder, sort them into units, and update the Wiki.
disable-model-invocation: true
---

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

1. Run `us courses current` and say which course you're working on. No course → stop and offer `/unistudent:course-setup`.
2. List the inbox folder (`inbox` in `us courses current`). Empty → tell the student where the inbox is (its folder name and path from `us courses current`), that they drop files into it (any files, any number; folders inside it are fine), and to run `/unistudent:course-add` again afterwards. Then stop.
3. Ask one question: which of these files are the lecturer's material (official), and where the others come from (e.g. "friend's summary", "my notes"). Default: added, origin unknown. Mention that official material wins when sources disagree, and that the files are moved out of the inbox into the Material folder (`official` or `added`, by unit).
4. Run `us add --json [--official "<file name>" ...] [--describe "<file name>=<where it comes from>" ...]`.
5. Files from the course site already have their unit. For the `unsorted` rest, propose a unit for each from its name and first page, show one list ("file → unit N / general"), and let the student confirm or change it in a single reply; record each confirmed one with `us assign "<path>" <unit|general>`. A recording of a whole class session (judge it from the whole file name and folder names, in any naming scheme) belongs to no unit: propose "Recorded lessons" for it and record it with `us assign "<path>" lessons`. Whatever is not confirmed stays unsorted (`us unsorted` lists it): never guess a unit into place.
6. The result's `wiki.images` and `wiki.needs_visual` list files with no text layer. **Delegate** them to the `source-reader` worker (one per item, given the whole item) so their content reaches the Wiki, then run `us wiki build` so `coverage.md` counts them.
7. If a unit that got new material has a study pack (`us study changes --unit N --json` shows `has_study_pack: true`), offer `/unistudent:study-pack N` to review proposed changes.
8. Report in two lines: what was added and where it went (the Material folder path).

Done when: the inbox is empty, every added file has a unit or the student deferred it, and scanned files were read.
