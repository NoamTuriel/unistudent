# Each worker names the model size it needs

Every worker used to run on the main conversation's model, usually the strongest and most expensive one, even for work a mid-size model does as well. Each worker file now has a `model:` line: `sonnet` for the recording-summarizer, source-reader, exam-indexer, exam-clusterer and verifier; `inherit` (the main model) for the wiki-unit-writer and study-pack-writer, which decide the quality of everything built on the Wiki.

We measured before choosing, on a real course, against what the main model had already written:

- **Sonnet** matched it on every test: the same announcements, exam hints and table of contents for a three-hour recording; every number, formula and graph detail of scanned pages; every question and page of an exam with handwritten solutions; all five errors planted in a study pack, and real ones besides.
- **Haiku** was cheaper per token but not per job. It lost exam hints from a recording (7 of 11), misread graph labels and guessed unreadable ones, put one exam question on the wrong page, and on long jobs used about twice Sonnet's tokens, which cancels most of its lower price. No worker uses it.

The exam-clusterer was not measured on its own; it does the same kind of work as the exam-indexer.

The same line serves every app. Claude reads `model:` itself (VS Code reads the same values in Claude-format agent files). There is no cross-app field for "a cheap model" or "a strong one", so the shared Delegate rule says in plain words what each value means (`haiku` small and fast, `sonnet` mid-size, `inherit` your strongest): any app that can start a subagent on a chosen model can act on it, and one that can't uses the model it has, as before. We did not generate separate agent files for Cursor, Gemini CLI, Codex or OpenCode: each has its own format and model names, Gemini is reported to refuse an agent file with a field it doesn't know, and these apps get the worker instructions through the Delegate rule and `us doc` anyway.
