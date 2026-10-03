# Before-the-test page: rules

One page for the whole course (not per unit), made once the Material folder holds past exams. It lives in the Study vault root, named by the course language (`Before the test`, `לקראת מבחן`), with its single-page question copies in a sibling folder (`Question pages`, `עמודי שאלות`). It belongs to the student: never overwrite an existing one, propose a new file or ask.

## What goes in

- **Every question of every past exam**, none dropped. A question is one entry: a multiple-choice question, an open question with its sub-parts (one entry), each true/false-claims question.
- **Exams in three shapes:** with a handwritten or annotated solution (the solution is on pages after, or on, the question's page), with a typed solution (answer key and worked answers on the last pages of the same file), and with no solution at all (the row says "no solution in the files"). Never assume "solution = next page": the indexer renders the pages and looks.
- **Sorted** by unit (the Wiki's unit pages decide, by what the question needs), then by similarity group, then easy to hard. A group is questions solved by the same method (not merely the same topic), from different exams, found by reading the question text, not only the skill line. Each group has a title and a one-line hint on what to master. A question that fits no group stands alone in its unit's "standalone" group.

## Each row

Exam name, question number, part, points, one-line skill; then the question link, and right beside it the solution link(s). Never the answer letter or any hint of the answer.

- Links are full `file:` links into the student's own files with `#page=N`, never into the Wiki.
- **Hide the answer:** when the solution is on other pages, the question links to a single-page copy (`pdfseparate -f N -l N`) in the question-pages folder; originals stay untouched. When the answer sits on the question's own page it cannot be hidden: link the original page and say so in the link text.

## Top of the page

A short intro, a unit navigation line, and a notes box saying what was not verified: that grouping, titles, hints and unit placement are the AI's classification and may be wrong, low-confidence rows, exams with no solution, and any step that could not run.

## Format

Follows the course format setting (Obsidian: foldable callout per group; Markdown: `<details>`). The student may ask for HTML, which opens in any browser (useful when the terminal has no right-to-left support). `us before-test build` writes all three.

## Refresh

The page is a snapshot. When a new exam is added, the page is stale until it is rebuilt (ask the student first, the cost is per exam).
