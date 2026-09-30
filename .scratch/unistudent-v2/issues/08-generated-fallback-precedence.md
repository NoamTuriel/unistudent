# 08: Document generated-fallback precedence over a later-installed real plugin

**What to build:** ADR 0005 says a generated fallback (university or course/subject) "behaves identically
to a hand-authored plugin from then on," but never says what happens once a *real* plugin for that
university or field is installed later. Pick one rule and write it down (extend ADR 0005, or a new ADR):
either the generated fallback keeps winning until the student explicitly asks to redo it, or an installed
real plugin takes over automatically the next time it's checked. If the answer is "a real plugin takes
over," `course-setup` step 1 and study-pack step 3 need a one-line check added (installed plugin found →
use it, regardless of an existing generated fallback for the same slug).

**Blocked by:** None

**Status:** ready-for-agent

- [ ] ADR 0005 (or a new ADR) states the precedence rule explicitly
- [ ] `course-setup` and `study-pack`'s "resolve the rules" steps match whatever the ADR says (no silent
      mismatch between doc and prose)
- [ ] If the rule is "real plugin wins," a test covers: generated fallback exists, then a matching real
      plugin/course skill becomes available — the real one is used, not the stale generated one
