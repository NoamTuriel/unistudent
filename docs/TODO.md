# TODO: known gaps

Remove an item when it ships.

## Setup: ask which lecture group the student is in, when the course has more than one
A university can run several lecture groups for one course, each with its own lecturer and its own recordings. During setup (and in `openu-sync`) check how many groups the course has, and if there is more than one, ask the student which one is theirs before downloading any recording. Show each group's name and lecturer next to its first recordings, so the student can recognise it.

How the mistake happened (Microeconomics, 2026-11-03):
- The course page has a side menu with one link, "recordings", that opens a single video collection. That collection was the accelerated group's, taught by a lecturer who is not the student's.
- The video collection page has a drop-down ("all video collections") that lists the others: the student's own group, an Arabic one, a set for a regular group, a set of review lessons. The sync skill (`references/site.md`, "Recordings") never says to open that drop-down, and never says that a course can have several groups.
- The skill read the first collection it found and treated it as "the course's recordings". Nothing asked the student which group they attend, and nothing showed the lecturer's name before the download.
- All 18 recordings (about 28 GB), their transcripts, the Wiki and 8 study packs were built from the wrong group's lectures, and the student only saw it after the packs were done. The files a lecturer attaches to a recording (booklets, exam-prep files) came in with that group too.
Fix: in setup and sync, list every collection in the drop-down, ask the student (one question), save the chosen group in the course settings, and have `us site-status` and every later sync use only that group's collection.
