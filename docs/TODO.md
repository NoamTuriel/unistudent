# TODO: known gaps

Open work found by the 2026-10-01 review and the work after it. Newest decisions first; remove an item when it ships.

## Decided, not yet built
- **Material sorting as its own feature.** Sorting the Material folder (by unit and trust level) must not depend on unit summaries: a student may never want them. Spec: does the Material folder keep unit and trust-level sorting without a study pack, and is the Study vault optional?

## Known gaps in what shipped
- **Wikilinks** (`[[page]]`) are not rewritten when a page moves, only Markdown links (Wiki and Study vault).
- **Moved files in the Study vault**: a link to a moved file is found again only when exactly one file in the Material folder has that name.
- **Word, OneNote and Google Docs copies** of study packs: `file:` links are untested there.
- **Hebrew folder and trust-level names** (`רשמי` / `נוסף` and the other labels in `course.py`) were chosen by the implementer; a Hebrew reader should review them.
- **No end-to-end test of the setup conversation** with a real AI (a sketch is in `evals/`).
- **Regression tests missing** for two review fixes of ticket 16: `us check` on an old-layout course must not flag in-course links, and old Wiki links must be rewritten when the course folder sits under a symlink (macOS `/tmp`, `/var`).

## Cleanup
- **Drop the old-layout compatibility** (`migrate.py`, `Course.legacy`) once every course folder has been migrated.
- Delete the history-rewrite backup mirror kept next to the repo once no longer needed.
