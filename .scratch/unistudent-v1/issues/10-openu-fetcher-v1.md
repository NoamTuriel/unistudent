# 10: OpenU fetcher v1 (Claude in Chrome)

**What to build:** The openu plugin lists the student's course site through Claude in Chrome and downloads every file into Raw with origin "course site", sorted into OpenU units. Interrupted downloads resume. It plugs into the core through the fetcher and sorting interfaces, so the core doesn't know about OpenU.

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] All non-recording files on the course site land in Raw with origin "course site" and are listed in the Manifest
- [ ] Files are assigned to OpenU units on clear evidence; others go to unsorted (reusing ticket 08's flow if available)
- [ ] A simulated interruption resumes without re-downloading completed files
- [ ] Sync tests (seam 1) pass against the saved site fixtures from ticket 01
- [ ] The core contains no OpenU-specific code
