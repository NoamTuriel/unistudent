# 07: Comprehensive project review against AI-plugin best practices

**What to build:** A written review doc (continuing the `docs/review-2026-09-30.md` convention, e.g. `docs/review-<date>-v2.md`) that audits the *entire* plugin as it ships after tickets 01-06 land, not just what's new in v2. It judges the shipped project against: (a) goal-fit — does it make it easy for a non-technical student to build a grounded per-course LLM wiki, get summaries, find where a teacher flagged something important in a recording, and get answers restricted to (and labeled against) course material; (b) AI-plugin best practice — skill/tool scoping and naming, context economy, portability across AI tools, deep-module design, skill composability/override correctness; (c) correct use of core agentic concepts — grounding/citation integrity, generic-vs-specific layering, the deterministic-script-vs-agent-judgment boundary, verification/self-checking loops. Since this is Noam's first AI plugin, every finding should explain *why* it matters, not just flag it.

**Blocked by:** 01, 02, 03, 04, 05, 06 (reviews the whole project as actually shipped, not a moving target)

**Status:** ready-for-agent

**Deferred:** not part of this implementation pass — filed for later.

- [ ] Reads the actual shipped code/skills fresh (re-read, not reasoned from prior conversation memory)
- [ ] Covers goal-alignment for a first-time, non-technical student explicitly
- [ ] Covers AI-plugin best practices: scoping, context economy, portability, deep-module design
- [ ] Covers agentic-concept correctness: grounding, layering, script-vs-agent boundary, verification loops
- [ ] Every finding explains why it matters, not just what to change
- [ ] Findings are prioritized, not just listed
- [ ] Produces a dated doc under `docs/`, plus a short list of any new follow-up tickets it surfaces
