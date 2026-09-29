# 08: Inbox and /add

**What to build:** The student drops any file in the inbox and runs `/add`. Each file moves into Raw with its origin and tier (official if the student marks it as the lecturer's, otherwise added), is assigned to a unit when the evidence is clear, and the Wiki is updated. Files that can't be placed are collected and asked about in one grouped question; answers are remembered.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] Inbox files end up in Raw exactly once, with origin and tier in the Manifest
- [ ] Clear-evidence files are assigned to a unit automatically; the rest go to unsorted
- [ ] One grouped question at the end resolves unsorted files; answers are stored and never asked again
- [ ] Wiki reflects the new files after `/add`
- [ ] `/add` reports what it did in a short summary
