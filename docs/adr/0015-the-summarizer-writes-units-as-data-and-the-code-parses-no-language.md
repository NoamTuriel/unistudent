# The summarizer writes a recording's units as data; the code parses no language

The Wiki needs to know which units a recorded lesson covers: a whole class session often teaches several, and each of them gets the lesson's table of contents on its unit page and in its study pack. Until v3 the code found them by reading words: the summary's first line had to say "a lesson about units 7-9" or "שיעור על יחידות 2 ו-3", and a regex knew the English and Hebrew unit words, "and" and "to" in both languages. Any other language named no units, and even in Hebrew the line had to be phrased just so ("the first unit" named nothing).

The recording-summarizer now writes the units as one language-free frontmatter line in `recording-summary.md`: `units: [3, 4]`, a list of integers, `[]` when the recording covers none. The AI already judges which units a lesson teaches; it hands that judgment over as data instead of as a sentence for the code to parse back. The one-line description stays, as text for the student. Summaries written before this line keep being read the old way, so no recording has to be summarised again.

The same rule applies to the other words the code used to know: the "Sources:" and "From:" line words and the unit word in file names come from the course language's label table, plus English always, instead of being hard-coded in Hebrew. Hebrew stays in the code only as the built-in Hebrew label table (and in the `openu` plugin, whose site is Hebrew).

We chose data over a parser per language because a parser is never finished (every language, every phrasing), and a wrong parse fails silently: a unit page quietly misses a lesson.
