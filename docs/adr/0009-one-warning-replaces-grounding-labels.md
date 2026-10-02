# One plain warning replaces the four grounding labels

Every paragraph used to carry one of four emoji (from the material, the AI's explanation of it, outside it, conflicts with it), and the student had to remember what each meant. It marked the normal case, rendered badly in right-to-left text, and added symbols to learn. This supersedes the four-label decision in `docs/spec/v1.md`.

Now a paragraph with no mark is from the course Wiki and cites a source file; the AI's own explanation of Wiki content is also unmarked and still cites. Only knowledge that does not come from the Wiki gets a warning in plain words, in the student's language, naming where it came from (general knowledge, or the web with a link). A conflict is a plain sentence ("the course says X; general practice differs: Y") inside such a paragraph. The hazard sign is the only emoji permitted anywhere in the repo, and a test enforces it. The wording lives once, in the course context template.

We chose this over keeping the labels with legends because the quiet default makes the one warning stand out, and over a different symbol because no symbol needs to be memorised when the warning says what it means. `us check --labels` flips accordingly: unmarked prose must cite, a warning paragraph need not. There is no migration: old marks in existing pages read as plain text and vanish when the page is rebuilt.

Shipped in unistudent 0.6.0: the grounding rule changed.
