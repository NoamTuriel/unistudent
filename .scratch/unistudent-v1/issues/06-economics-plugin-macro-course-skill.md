# 06: Economics subject plugin with the macro course skill

**What to build:** The economics plugin ships the economics field skill and the macro course skill, ported from `macro-unit-summary`. Per-semester facts (lecturer, paths, recording-to-unit mapping) move to Settings. At setup the student picks a course skill by name; a macro study pack then follows the macro rules on top of the economics and generic rules.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] Setup lists installed course skills by name; choosing one records it in Settings
- [ ] Rule order generic → field → course is applied; course overrides field overrides generic
- [ ] The macro course skill contains no per-semester or per-student facts
- [ ] A macro study pack uses the five-part concept structure and macro page set
- [ ] The economics plugin has no dependency on the openu plugin
