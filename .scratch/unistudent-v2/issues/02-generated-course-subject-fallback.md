# 02: Generated course/subject fallback

**What to build:** Apply ticket 01's interview-generate-persist mechanism one level down. When a student's course has no matching subject/course skill, they're interviewed once about what to emphasize and how to summarize, and the plugin generates a persistent study-pack rules file (same shape as `plugins/economics/skills/macro/SKILL.md`) instead of silently falling back to only the generic rules with no course-specific emphasis. Reuses ticket 01's generation mechanism rather than building a second one.

**Blocked by:** 01 (reuses its interview/generate/persist mechanism)

**Status:** done (2026-09-30)

- [x] Study-pack build checks, in order: an installed subject/course skill, then a previously generated fallback at `~/.unistudent/generated/<subject-slug>/<course-slug>.md`, then falls through to the interview
- [x] The interview asks what to emphasize and how the course wants material summarized, shows findings back to the student before persisting
- [x] A confirmed interview writes a rules file in the same shape as `plugins/economics/skills/macro/SKILL.md`
- [x] A second study-pack build for the same course reuses the generated file with no re-interview
- [x] The generated fallback never contains university/site-access knowledge (per ADR 0001 / ADR 0005)
- [x] Tests cover: interview → generated file shape, and reuse-without-re-interview on a second run
