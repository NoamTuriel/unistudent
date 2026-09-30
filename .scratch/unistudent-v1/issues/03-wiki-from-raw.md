# 03: Wiki from Raw

**What to build:** The student runs `/wiki` and gets a Wiki built from Raw: every PDF and Word file converted to Markdown with formulas preserved, an index, one page per unit, a glossary in the course's notation, and a question bank tagged by unit and topic. Every Wiki page lists its sources. The Wiki can be deleted and rebuilt from Raw with the same result.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Word files are converted via PDF so formulas survive; PDFs convert to Markdown
- [ ] Wiki has an index, unit pages (including approved methods, notation and assumptions when found), a glossary and a question bank
- [ ] Every Wiki page records its sources (file + page)
- [ ] Deleting the Wiki and rebuilding gives an equivalent Wiki
- [ ] Wiki-build tests (seam 2): a small fixture course folder produces the expected set of pages
