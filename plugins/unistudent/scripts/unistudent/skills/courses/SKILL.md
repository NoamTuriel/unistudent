---
name: courses
description: List the student's courses and switch the active one.
disable-model-invocation: true
---

<!-- conventions: keep identical in every UniStudent skill -->
Conventions. `us <command>`: the UniStudent tool for that command, the MCP tool named by its words joined with `_` (`us wiki build` → `wiki_build`, options as named arguments) when the unistudent MCP server is connected; otherwise run `unistudent <command> --json` in a shell (inside the plugin: `python3 <this skill's base directory>/../../../us.py <command> --json`; `python` on Windows). **Delegate** to a worker: its instructions are in `<this skill's base directory>/../../agents/<worker>.md` (if that file isn't there, get them with `us doc <worker>`); give them to a subagent if you can run subagents (in parallel when there are several), otherwise follow them yourself, one at a time. **Ask**: use your question tool if you have one, otherwise ask in the chat.
<!-- /conventions -->

1. Run `us courses list`. Show the courses; the active one is starred.
2. If the student names a course, run `us courses switch "<name>"` and confirm with "Working on: <name>".
3. Remind them in one line: in Cowork, each course works best as its own project with that course folder connected; in Claude Code, start Claude inside the course folder. Either way, answers come only from that course's Wiki.

Done when: the student knows which course is active.
