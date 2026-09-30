# 03: Setup progress state + resume

**What to build:** `course-setup` writes down which stage it has completed after every stage (university/course/path/format/fetch-and-organize/analyze/capabilities), to a small state file next to the course's hidden settings. If the student stops setup (it's slow, or they close the session) and comes back later, re-running setup (or `course-help` detecting incomplete setup) resumes at the next unfinished stage with prior answers intact, instead of restarting from scratch.

**Blocked by:** None

**Status:** done (2026-09-30)

- [x] A stage-state file records the last completed stage and the answers already given, updated after each stage completes
- [x] Re-running `course-setup` on a course with incomplete state resumes at the next unfinished stage, not stage one
- [x] `course-help` detects incomplete setup and offers to resume it
- [x] Long-running stages (fetch, analyze) rely on their own existing finer-grained resumability (manifest-driven sync, per-file recording jobs) — this ticket's state file only tracks stage-level "in progress" vs. "done", it does not duplicate that finer resumability
- [x] A test stops setup after each stage in turn and asserts a fresh run resumes at the correct next stage with prior answers intact
