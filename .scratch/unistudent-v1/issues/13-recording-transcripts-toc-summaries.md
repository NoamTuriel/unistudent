# 13: Recording transcripts, tables of contents and summaries

**What to build:** Before processing, the plugin warns that transcription is heavy and slow and shows an estimate from a quick benchmark on this machine. On approval, each recording gets a Hebrew transcript, a timestamped table of contents (explanation / example / practice / exam question / review / announcements / lecturer to camera) and a summary with announcements and "always on the exam" moments, all in the Wiki. One subagent per recording. Works on any OS and on imported recordings, and can be limited to one unit.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] No transcription starts without an explicit yes after the estimate
- [ ] Transcription runs on macOS, Windows and Linux (backend chosen per machine)
- [ ] Each processed recording has transcript, table of contents with timestamps and summary in the Wiki
- [ ] Unit-only processing works; the main conversation receives only summaries
- [ ] Video level choice is saved in Settings
