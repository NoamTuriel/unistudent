# 14: Multiple courses

**What to build:** A student with several courses runs `/courses` to list and switch them. Every command first announces the active course ("working on: Macro") or asks which course when it can't tell. Material from another course the student takes is labeled "from your other course, not this one".

**Blocked by:** 02, 04

**Status:** ready-for-agent

- [ ] `/courses` lists all Registry entries and switches the active course
- [ ] Every command announces the active course, or asks when missing or ambiguous
- [ ] Each course folder has its own Wiki; answers never cite another course's Wiki unless the student asks for a comparison
- [ ] Grounding eval includes a cross-course case with the expected label
