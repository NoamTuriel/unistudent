---
name: courses
description: List the student's courses and switch the active one.
disable-model-invocation: true
---

`us` means `python3 <this skill's base directory>/../../scripts/us.py`.

1. Run `us courses list`. Show the courses; the active one is starred.
2. If the student names a course, run `us courses switch "<name>"` and confirm with "Working on: <name>".
3. Remind them in one line: in Cowork, each course works best as its own project with that course folder connected; in Claude Code, start Claude inside the course folder. Either way, answers come only from that course's Wiki.
