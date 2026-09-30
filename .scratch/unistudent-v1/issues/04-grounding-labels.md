# 04: Grounding labels

**What to build:** In a course folder, every chat answer about the course carries one grounding label per paragraph: ✅ from course material (with sources), ⚠️ not in course material, ❌ conflicts with the course (course version first, difference explained). Answers the Wiki doesn't cover say so and point to the inbox. Official material wins over added material; added material is labeled with its origin. The rule is loaded through the course context file, so it applies without any skill triggering.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] The course context file loads the grounding rule in both Cowork and Claude Code
- [ ] Each paragraph of an answer carries exactly one grounding label; ✅ paragraphs list sources that exist in the Wiki
- [ ] Uncovered questions are answered as not covered, with an inbox suggestion
- [ ] Official beats added on conflict; added material shows its origin
- [ ] Outside knowledge appears only when the student asks, and is labeled ⚠️
- [ ] Grounding eval (seam 3): fixed questions against a fixture Wiki get the expected labels and valid citations
