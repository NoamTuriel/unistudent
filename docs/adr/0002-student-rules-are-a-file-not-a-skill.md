# Student preferences are a file the core reads, not a skill

When a student changes how material is handled or how study packs look, the change is stored as a rules file inside the course folder, and the core reads it before every study-pack build. A per-student skill would be more natural, but Cowork doesn't load skills from a connected folder, so a skill would only work in Claude Code.

Skills are never modified by student requests: published skills stay identical for every student, and all personalisation lives in the student-preferences file.
Preferences have two levels: course preferences (in the course folder) and general preferences (for all courses); course preferences win.
