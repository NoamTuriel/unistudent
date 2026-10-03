# TODO: known gaps

Remove an item when it ships.

## Revisit the course-specific skills (economics, macro)
In ticket 20 the owner built unit Study packs from the generic rules alone and they were good. Decide whether the course skills earn their place:
- Read what the economics and macro skills add on top of the generic rules.
- Build a partial pack with and without them and compare.
- Keep them (then one field skill per major is needed: math, physics, computer science, and so on) or fold the useful parts into the generic rules and drop them.

## Practice page: question number, page, and the solution link right next to it
Today the practice page (`N.3 תרגול`) lists questions per topic, but the student can't jump straight from a question to its answer. Seen in the Macroeconomics course (2026-10-03): the student failed a question, then had to hunt for the solution page in a different file.
Change the rules so each practice row has:
- the question number and the source file page (`שאלה 3, עמוד 4`);
- a link to the question (full `file:` link with `#page=N`);
- a link to its solution right beside it (same file, other page, or the solutions file), or "no solution in the files" when there is none.
Also group by similarity, not only by topic: if the student fails one question and then understands the solution, the next question in the group should test the same idea (a group of 3-8, from different sources, easy to hard), with a one-line hint on what to master.
Hide-the-answer option: when the question page also shows the solution (handwritten answers on the same page, or the solution on the next page of the same PDF), offer a single-page copy of the question page (`pdfseparate -f N -l N`) in the Study vault, and link the question to that copy. Never modify the student's original file. Where the answer is on the same page and can't be hidden, say so in the link text.
Source of the solution page: the exam PDFs in this course have the handwritten solution on the page after the typed question page, and the typed answer key near the end. Don't assume this layout, check it (render the page and look) before linking.

## Before-the-test page for the whole course (past exam questions)
New course-level page, made once per course (not per unit), when past exams exist in the Material folder. Proposed name: `לקראת מבחן` / `Before the test`, in the Study vault root of the course. Built in the Macroeconomics course on 2026-10-03 by hand (225 questions from 15 exams), and it worked well. What it should do:
- Index every question of every past exam: exam name, part (A multiple choice, B open, C claims), question number, question page(s), solution page(s), unit, topic, a one-line skill, points. Use one subagent per 2 exams, with a shared spec file, and a low-resolution render of the solution pages to check the page mapping. Do not trust "solution = next page" blindly (some exams put annotated copies at the end, some need 3-5 pages per question).
- Cluster the questions into groups of similar questions (method, not just topic), sorted by unit, then easy to hard, mixing exams. A final subagent does the clustering over the whole index, and it must read the question text, not only the skill line.
- Each row: question link, solution link right beside it (see the practice page item above), no answer letter shown.
- Include the exams that have only a typed solution (here: 2026 exams, answer key and worked answers on the last two pages) and exams with no solution at all (mark them "no solution in the files").
- Needs `us` support or a script for: listing exam files, splitting single pages, and writing the HTML or Markdown. Ask the student before making it (it is a big job: 15 exams cost about 600K subagent tokens).
- Output format follows the course settings (here Obsidian Markdown by default; the test run used HTML so the student could open it in the browser, because the terminal has no RTL).
- Check `us check` accepts it: the page links to files in `2-חומרי-הקורס`, not to the Wiki.
Also open: decide how the page is refreshed when the student adds a new exam (`study changes` should report "new exam file, before-the-test page is stale").
