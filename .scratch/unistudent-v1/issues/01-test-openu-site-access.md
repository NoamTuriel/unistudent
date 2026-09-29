# 01: Test OpenU site access

**What to build:** A research note that tells the fetcher how to work: how the OpenU course site is structured, how the file list and recordings are reached, whether a script can reuse the student's logged-in Chrome session, and whether OpenU's terms allow students to download recordings for personal use. Saved copies of real course pages become the test fixtures for the site branch.

**Blocked by:** None (can start immediately)

**Status:** done (2026-09-30)

- [x] Note describes the course site structure (sections, file entries, recordings) with the URL patterns the fetcher needs
- [x] Note states, with evidence, whether a Python script can reuse the Chrome session (and how), or why not
- [x] Note states what OpenU's terms say about downloading recordings, with the source quoted
- [x] Anonymised HTML copies of a course home page, a unit/section page and a recordings page are saved as fixtures (no personal data, no course content beyond structure)
- [x] Note lists open risks for ticket 10 (e.g. rate limits, expiring links, streaming-only video)

## Findings

See `plugins/openu/skills/openu-sync/references/site.md`. In short: `/course/resources.php` lists every file with its section; `view.php?id=…&redirect=1` returns the file; downloads work from inside the logged-in tab (verified with one 184 KB PDF); recordings are tokenised HLS streams that need no cookies (downloaded with ffmpeg); the session cookie is http-only, so scripts can't reuse it; the site footer allows personal use by the course's students only and forbids distribution.

Not done: anonymised HTML fixtures of real pages (the parser runs in the browser, so tests use a synthetic listing instead).
