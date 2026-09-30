# 07: Student preferences

**What to build:** When the student asks for a change that affects a whole unit's study pack or how material is handled, the plugin asks "only this unit, always for this course, or for all my courses?" and saves the answer to course preferences or general preferences. Preferences are applied on every study-pack build. Edits to a single paragraph are made without asking and never saved. Skills are never modified.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Whole-unit change requests trigger the three-way question; paragraph edits don't
- [ ] "This course" writes course preferences in the course folder; "all my courses" writes general preferences next to the Registry
- [ ] Course preferences win over general preferences; both win over skills
- [ ] No skill file is ever changed by a student request
