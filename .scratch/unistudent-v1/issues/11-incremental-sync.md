# 11: Incremental /sync

**What to build:** A second `/sync` downloads only files that are new or changed since the last sync and reports what changed.

**Blocked by:** 10

**Status:** ready-for-agent

- [ ] Unchanged files are not downloaded again (checked via the Manifest)
- [ ] New and changed files are downloaded and reported in a "what's new" summary
- [ ] Sync test: a second run against updated fixtures reports only the difference
