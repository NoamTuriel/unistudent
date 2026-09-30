# 04: Token-friendly recording frame analysis

**What to build:** Visual frame analysis of recordings (`mcp-video-analyzer`'s `get_frame_at`/`analyze_moment`, called per segment by `recording-summarizer`) becomes its own explicit opt-in with a shown cost estimate (segments × one vision call each), never silently triggered just because the MCP server happens to be installed and the student picked recording level 3. This closes the current spec/implementation mismatch: v1 explicitly deferred frame-based analysis to "video level 2" / out of scope, but the code already does it opportunistically.

**Blocked by:** None

**Status:** done (2026-09-30)


- [x] `course-recordings` shows a separate cost estimate and asks a separate yes/no for frame analysis, distinct from the existing recording-level question
- [x] `recording-summarizer.md` never calls `get_frame_at`/`analyze_moment` unless that opt-in was explicitly chosen, regardless of whether `mcp-video-analyzer` is installed
- [x] The choice is remembered per course (same pattern as the existing recording-level setting)
- [x] A test confirms recording-summarizer's behavior differs correctly with the opt-in on vs. off, holding recording level constant
