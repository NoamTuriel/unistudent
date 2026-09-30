# 09: `us generated list` — visibility into generated fallbacks

**What to build:** Tickets 01/02 write generated university and course/subject fallbacks to
`~/.unistudent/generated/`, but nothing lets a student (or `course-help`) see what's been generated,
when, or for what. Add a `generated` command (mirroring `setup-progress list`'s shape) that lists every
generated fallback under `~/.unistudent/generated/`, with its path and a one-line preview. Surface it from
`course-help` alongside the existing incomplete-setup check (ticket 03), so a student who forgot they
answered an interview six months ago can find and re-read (or delete) it.

**Blocked by:** 01, 02 (lists what those tickets write)

**Status:** ready-for-agent

- [ ] `us generated list --json` returns every file under `~/.unistudent/generated/`, university and
      course/subject fallbacks both, with path and a short preview
- [ ] `course-help` mentions generated fallbacks exist when there are any (not only on request)
- [ ] A test covers: no generated fallbacks → empty list; one of each kind → both appear
