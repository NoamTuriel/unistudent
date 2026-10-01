# TODO: known gaps

Open work found by the 2026-10-01 review and the work after it. Newest decisions first; remove an item when it ships.

## Decided, not yet built
- **Material sorting does not depend on Study packs.** The Material folder keeps its trust-level and unit sorting for every student, whether or not they ever build a Study pack. Write the spec: what sets a unit when there is no Study pack, and how `us unsorted` behaves.
- **The Study vault is created at the first Study pack**, not at setup. A student who only wants answers sees two folders (Inbox, Material folder). Update ADR 0007 ("three visible folders"), the setup text and the README when this ships.
- **Docs tools for Word, OneNote and Google Docs students.** When a student chooses one of these, setup recommends installing a docs tool for it (the way ticket 12 recommends plugins), and Study packs are then written through that tool. Every platform has links; do not invent a converter. Spec first: which tool for which platform, and how `file:` links behave in each.

## Known gaps in what shipped
- **Moved files in the Study vault**: a link to a moved file is found again only when exactly one file in the Material folder has that name; otherwise the link stays and `us check` flags it.
- **No end-to-end test of the setup conversation** with a real AI (a sketch is in `evals/`).
- Wikilinks need no work: Study packs never contain `[[wikilinks]]`; their citations are `file:` links (ticket 16).

## Cleanup
- Done in 0.5.0: the old-layout code (`migrate.py`, `Course.legacy`) was removed; an old-layout folder is refused with a pointer to version 0.4.2.
