# TODO: known gaps

Open work found by the 2026-10-01 review and the work after it. Every item below was settled in a grilling session with the owner; remove an item when it ships.

## Build order
1. Done in 0.5.4: the transcription guard (`us recordings approve`) and the matplotlib order (ticket 17).
2. Done in 0.6.0: simple Study packs (ticket 18), the lazy Study vault and unit on arrival (ticket 19).
3. Then: docs tools.

## After that
- **Docs tools for Word, OneNote and Google Docs students.** Setup recommends a docs tool for the chosen platform (the way ticket 12 recommends plugins), and Study packs are written through it. Spec first: which tool for which platform, and how `file:` links behave in each. Do not invent a converter.

## Cleanup
- Done in 0.5.0: the old-layout code (`migrate.py`, `Course.legacy`) was removed; an old-layout folder is refused with a pointer to version 0.4.2.
