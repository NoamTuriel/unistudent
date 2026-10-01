# TODO: known gaps

Open work found by the 2026-10-01 review and the work after it. Every item below was settled in a grilling session with the owner; remove an item when it ships.

## Build order
1. Done in 0.5.4: the transcription guard (`us recordings approve`) and the matplotlib order (ticket 17).
2. **0.6.0**: all the Study pack changes in one pass (bloat, links, Practice page, accepted reasoning). They all rewrite `reference/study-pack.md` and the economics skill, so check them against one real unit pack.
3. Then: the lazy Study vault, then Material sorting, then docs tools.

## 0.6.0: Study pack changes
- **Every part earns its place.** The template bends to the subject: no "Formula: none" line, no forced memory trick. Rewrite the concept structure in `study-pack.md` and the economics skill's "always these five parts". Grounding emoji (✅ 💡 ⚠️ ❌) stay in packs as they are; ticket 16 is unchanged.
- **One "In the lectures" line per topic instead of a link on every paragraph.** Each topic ends with the recording and time, linked once, and a "From:" line naming the source files. With no link, show the file name. A topic no recording covered gets no line; a recording with no transcript shows its file name without a time. `us check` verifies each topic's closing line and that its links resolve. Chat answers keep their links on every claim (ticket 16 applies there).
- **The Practice page (`N.3`) gets simple.** It opens with a table of topics (topic, number of questions). Under each topic: the suited questions from easy to hard, each a link to its question file with a one-line note on what it exercises. It ends with the **Short version** (CONTEXT.md), explained in one line under its heading. No stages, no topic tags, no per-question recording links, no graphs. The separate `N.3b` page and the "practice-short" row are removed. The Recordings index (`N.4`) is unchanged.
- **Accepted reasoning moves inside each topic.** A short "How to answer" block after the topic's concepts: the model answer as a chain, the solutions' own wording quoted, and the steps that must be justified rather than assumed. Empty parts are not written; a topic with no verbal answered questions gets no block. The roadmap only points to it. Update the generic rule and the economics rule together.
- **Graphs stay in topics** only where the course draws that concept with one; never on the Practice page.
- **Audit the pack for other clutter** with a real unit pack open: repeated headers, boxes, callouts, navigation lines, captions. Cut until only what a student reads remains.

## After that
- **The Study vault is created at the first Study pack**, not at setup (ADR 0008). Update the setup text and the README; a missing Study vault is never reported as a problem.
- **Material sorting does not depend on Study packs.** The unit is set when the file arrives: the university plugin knows it from the course site (OpenU: from the download); otherwise the AI proposes a unit from the file name and first page, shows one list, and the student confirms or changes it in one reply. Files not confirmed stay "unsorted"; `us unsorted` lists exactly those. No new command.
- **Docs tools for Word, OneNote and Google Docs students.** Setup recommends a docs tool for the chosen platform (the way ticket 12 recommends plugins), and Study packs are written through it. Spec first: which tool for which platform, and how `file:` links behave in each. Do not invent a converter.

## Known gaps, no decision needed yet
- **Moved files in the Study vault**: a link to a moved file is found again only when exactly one file in the Material folder has that name; otherwise the link stays and `us check` flags it.
- **No end-to-end test of the setup conversation** with a real AI (a sketch is in `evals/`).
- Wikilinks need no work: Study packs never contain `[[wikilinks]]`; their citations are `file:` links (ticket 16).

## Cleanup
- Done in 0.5.0: the old-layout code (`migrate.py`, `Course.legacy`) was removed; an old-layout folder is refused with a pointer to version 0.4.2.
