---
name: course-help
description: Explain how UniStudent works and what it can do next.
disable-model-invocation: true
---

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); as the Claude plugin, give them to the plugin's subagent of that name, which has the UniStudent tools (in parallel when there are several); in any other app, follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

1. Run `us setup-progress list --json`. Any entries → tell the student setup for that course stopped partway (after its last recorded stage) and offer to resume it with `/unistudent:course-setup`.
   Run `us generated list --json` too. Any entries → mention once that earlier interviews were saved (show each one's preview and path) and that the student can re-read or delete them.
2. Run `us courses current --json`. No course → say so and offer `/unistudent:course-setup`. Otherwise start with "Working on: <name>".
3. Explain from the course folder's `README.md`, in the student's language and in the student's words: the flow (course material → Wiki → study packs), the three folders (inbox, Material folder, Study vault: open that one as the vault), and the warning on anything not from the course material. Keep it to what fits one screen.
4. Show what is waiting, from real state:
   - `us unsorted --json`: files that need a unit.
   - `us recordings list --json`: recordings not processed.
   - The inbox folder (`inbox` in `us courses current`): files not added yet.
   - Units without a study pack: the Wiki's `units/` (in the folder `wiki` names) compared with the unit folders in the Study vault (`study`; if it does not exist yet, no unit has a pack).
5. Offer, one line each, the commands from the `README.md` command table that match what step 4 found, plus the university plugin's sync skill (e.g. `/openu:openu-sync`) when there is new material on the course site.

Done when: the student has seen what's waiting and the commands that apply.
