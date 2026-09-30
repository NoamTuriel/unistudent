---
name: course-help
description: Explain how UniStudent works and what it can do next.
disable-model-invocation: true
---

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

1. Run `us setup-progress list --json`. Any entries → tell the student setup for that course stopped partway (after its last recorded stage) and offer to resume it with `/unistudent:course-setup`.
2. Run `us courses current --json`. No course → say so and offer `/unistudent:course-setup`. Otherwise start with "Working on: <name>".
3. Explain from the course folder's `README.md`, in the student's language and in the student's words: the flow (course material → Wiki → study packs), the inbox, and the grounding labels. Keep it to what fits one screen.
4. Show what is waiting, from real state:
   - `us unsorted --json`: files that need a unit.
   - `us recordings list --json`: recordings not processed.
   - `ls inbox/`: files not added yet.
   - Units without a study pack: `wiki/units/` compared with `study/`.
5. Offer, one line each, the commands from the `README.md` command table that match what step 4 found, plus the university plugin's sync skill (e.g. `/openu:openu-sync`) when there is new material on the course site.

Done when: the student has seen what's waiting and the commands that apply.
