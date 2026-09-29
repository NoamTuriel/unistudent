# 05: Generic study pack

**What to build:** `/unit N` shows the page picker (every page with a one-line "what it gives you", all selected by default), builds the unit's topic list, and writes the selected default pages (roadmap, walkthrough, practice by topic, recordings table of contents) from the Wiki using the generic rules. Every paragraph carries a grounding label. A verifier subagent checks the pack before it is handed over.

**Blocked by:** 03, 04

**Status:** ready-for-agent

- [ ] Page picker lists all available pages with descriptions; defaults to all
- [ ] One topic list (4–6 topics with tags) is shared by every page of the study pack
- [ ] Each selected page is written in the student's chosen format (Obsidian or plain Markdown) in the course's language
- [ ] Verifier reports zero broken links, zero missing timestamps and zero paragraphs without a source before completion
- [ ] One unit-pack writer subagent per unit; the main conversation receives only the result summary
