# 01: Test OpenU site access

**What to build:** A research note that tells the fetcher how to work: how the OpenU course site is structured, how the file list and recordings are reached, whether a script can reuse the student's logged-in Chrome session, and whether OpenU's terms allow students to download recordings for personal use. Saved copies of real course pages become the test fixtures for the site branch.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Note describes the course site structure (sections, file entries, recordings) with the URL patterns the fetcher needs
- [ ] Note states, with evidence, whether a Python script can reuse the Chrome session (and how), or why not
- [ ] Note states what OpenU's terms say about downloading recordings, with the source quoted
- [ ] Anonymised HTML copies of a course home page, a unit/section page and a recordings page are saved as fixtures (no personal data, no course content beyond structure)
- [ ] Note lists open risks for ticket 10 (e.g. rate limits, expiring links, streaming-only video)
