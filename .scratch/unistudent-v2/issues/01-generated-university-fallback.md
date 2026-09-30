# 01: Generated university fallback

**What to build:** When a student picks a university with no installed plugin, `course-setup` interviews them once (site URL, how they organize/prioritize material) instead of telling them to go find a plugin. The interview's findings are shown back to the student for confirmation, then written to a persistent local reference file (same shape as `plugins/openu/skills/openu-sync/references/site.md`) under `~/.unistudent/generated/<university-slug>/site.md`. From then on, setup for that university reuses the generated file instead of re-interviewing. This replaces `course-setup`'s current dead-end branch ("say downloading needs their university's plugin").

**Blocked by:** None (can start immediately)

**Status:** done (2026-09-30)

- [x] `course-setup` checks, in order: an installed university plugin, then a previously generated fallback at `~/.unistudent/generated/<university-slug>/site.md`, then falls through to the interview
- [x] The interview asks for the site URL and how the student organizes/prioritizes material, and shows findings back to the student before persisting anything
- [x] A confirmed interview writes a reference file in the same shape as `plugins/openu/skills/openu-sync/references/site.md`
- [x] A second `course-setup` run for the same university reuses the generated file with no re-interview
- [x] The generated fallback never contains study-pack rules (per ADR 0001 / ADR 0005 — university axis stays separate from subject axis)
- [x] Tests at the existing seams (`tests/test_course_folder.py` or a new seam matching the project's fixture style) cover: interview → generated file shape, and reuse-without-re-interview on a second run
