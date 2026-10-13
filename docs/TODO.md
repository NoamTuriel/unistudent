# TODO: known gaps

Remove an item when it ships.

## Practice page: question number, page, and the solution link right next to it
Today the practice page (`N.3 תרגול`) lists questions per topic, but the student can't jump straight from a question to its answer. Seen in the Macroeconomics course (2026-10-03): the student failed a question, then had to hunt for the solution page in a different file.
Change the rules so each practice row has:
- the question number and the source file page (`שאלה 3, עמוד 4`);
- a link to the question (full `file:` link with `#page=N`);
- a link to its solution right beside it (same file, other page, or the solutions file), or "no solution in the files" when there is none.
Also group by similarity, not only by topic: if the student fails one question and then understands the solution, the next question in the group should test the same idea (a group of 3-8, from different sources, easy to hard), with a one-line hint on what to master.
Hide-the-answer option: when the question page also shows the solution (handwritten answers on the same page, or the solution on the next page of the same PDF), offer a single-page copy of the question page (`pdfseparate -f N -l N`) in the Study vault, and link the question to that copy. Never modify the student's original file. Where the answer is on the same page and can't be hidden, say so in the link text.
Source of the solution page: the exam PDFs in this course have the handwritten solution on the page after the typed question page, and the typed answer key near the end. Don't assume this layout, check it (render the page and look) before linking.

## Recordings: offer a low-quality or audio-only download (discuss first)
A student who wants the course to know a recording but won't watch it could download a smaller copy. Checked in the code on branch `v3` (2026-10-13), not on the live site:
- Low-quality video: not possible today. `recordings fetch` runs ffmpeg with no variant choice, so it takes the highest quality (about 0.81 GB per hour). The site notes say there is a second variant at about 0.4 Mbit/s (about 0.18 GB per hour). A few lines would pick it (`-map 0:p:<N>`, or the lowest-bandwidth URI from the master playlist), if the stored stream link is a master playlist. Unverified.
- Audio only: works today (`--audio-only`, about 58 MB per hour at ffmpeg's default AAC rate), but probably still downloads the full video and drops the picture, so it saves disk, not download time.
Decide whether the Fetch plan offers "smaller copy" per recording, and what it means for frame analysis (needs the video).

## Before-the-test page: refresh when an exam is added
The page (skill `before-test`) is a snapshot. Decide how it is refreshed: `study changes` should report "new exam file, before-the-test page is stale".

## Found by the v3 self-test on synthetic courses (2026-10-14), not fixed
- `us check` verifies that a `file:` link's file exists, not that its `#page=N` exists in the PDF: a solution link to the wrong page passes.
- `us wiki check` counts a unit page as sourced because its generated block has a `Sources:` line, so an unsourced bullet a worker writes below it passes.
- A `.pptx` slide cannot be linked by page (`#page=` works in PDFs only). With LibreOffice the kept PDF in `.unistudent/view/` could be the link target, but the Study vault never links into the hidden folder: decide.
- Files the student unticks in the Fetch plan come back in every later plan (nothing remembers "skip this one").
- The material can contradict itself (an answer key with a wrong count): no worker step says to flag it to the student.
- The verifier flags a term that is in the material but missing from the glossary, and no pack step can fix the Wiki: decide who does.
- Unverified on the live site: file sizes from the HEAD probe, recording lengths next to titles, whether a sound-only fetch still downloads the whole stream.
